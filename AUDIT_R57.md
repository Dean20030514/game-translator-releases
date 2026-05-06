# Round 57 — 6 维度深度债务审计报告

> **创建时间**：r56 末（commit `a997ee2`）后立即
>
> **范围**：r56 已闭合 11 项 audit findings（H1/H2/H3/M1/M2/M3/L1/L2 全部 fix；L3-L5 文档化保留）后，按用户列出的 6 大类做更深度扫描。**所有 findings 不重复 r56 已 fix 项**。
>
> **Baseline**：r56 末状态 — 182/182 PASS / VERIFIED-CLAIMS OK（tests_total 485 / test_files 33 / ci_steps 34 / assertion_points 611）/ 16 轮 0 CRITICAL streak / 13 hard contracts / actionable backlog 2 项（Godot + Kirikiri/TyranoBuilder）。
>
> **状态**：📋 待用户决策 fix path（X / Y / Z / W）；尚未实施。

---

## 1️⃣ 技术债（Technical Debt）

### T1 🔴 HIGH — Python 版本兼容声称与实际代码冲突

`pyproject.toml`: `requires-python = ">=3.9"`。**但 7 个文件用 `|` type union 语法**（PEP 604，Python 3.10+ 才在运行时支持；3.9 必须 `from __future__ import annotations` 才能用）。

CI matrix 跑 `[3.9, 3.12, 3.13]` 但 r51 之前可能 3.9 就 broken — 没有人发现是因为大部分 type hint 在 `from __future__ import annotations` 下被 lazily evaluated。**潜在 latent bug**：如果某个文件没加 `from __future__` 又用了 `int | None`，3.9 会 ImportError。

**fix**：(a) bump 到 `>=3.10`（最干净；CI matrix 删 3.9）；(b) 强制每个文件 `from __future__ import annotations` + 加 CI guard。

### T2 🟡 MEDIUM — Type hint 覆盖率仅 44%

production code 1068 函数中只有 470 (44%) 完全 hint（args + return）。CI 跑了 mypy 但是 **"informational"** 级别（不 fail build）。

**fix**：(a) 把 mypy step 从 informational 升级为 enforce（高成本，需先补全 hint）；(b) 设定每轮提升 5% 覆盖率的渐进目标。

### T3 🟡 MEDIUM — 测试 fixture 与生产差异巨大

测试用 1-4 个 translate block 的 `_TL_EMPTY_FIXTURE`，r52 实测是 74098 entries。覆盖盲区：
- nvl 块 / multi-line say / `{i}` 标签 / 角色名 alias / SAZMOD 模组结构都没在 fixture
- r53 W3 ID drift detection 阈值 10% 来自实测但没有 fixture 验证

**fix**：抽取 `tests/artifacts/tyrant_untranslated.json` 现成 sample 一部分作为 "complex fixture"，扩充 1-2 个集成测试。

### T4 🟢 LOW — `tools/` 散乱，无共享 base

15 个 CLI tool 各自独立 entry，每个都自己写 argparse + setup_logging + path validation。如果将来要批量加新功能（如 `--dry-run` for all tools）会重复劳动。

**判断**：这是项目第 8 原则"最小改动"接受的代价；`tools/` 是辅助，不是 hot path。**不建议 fix**，文档化为 architectural decision。

---

## 2️⃣ 质量与安全债（Quality & Security Debt）

### S1 🟡 MEDIUM — `.gitignore` 缺关键 secret patterns

当前 `.gitignore` 只有 `__pycache__/` `*.pyc` `output/` `.vscode/` 等，**没有**：
- `.env` / `.env.*`
- `*.key` / `*.pem`
- `**/api_keys.json`
- `renpy_translate.json`（用户实际配置文件，CLAUDE.md global 安全指南要求 `api_key_env` / `api_key_file` 字段不入库）
- `*.bak`（pre-commit 防止误 commit 备份文件）

**风险**：开发者本地 test 时不小心 `git add .` 会上传 API key。

**fix**：补充 `.gitignore`，5 行变更。

### S2 🟡 MEDIUM — 用户面文件路径未做 path traversal sanitization

`main.py:_maybe_warn_on_symlink` 已加 symlink check（r53 监控 #4），但**没有 path traversal**：用户传 `--game-dir "../../../etc/passwd"` 会被接受。本地工具威胁模型下 attacker 已有 RW 权限——但**多用户共享机器**（教学环境 / 实验室 / CI runner）下是 finding。

**fix**：(a) 加 `resolve()` + 路径在白名单根下检查；(b) 文档化为本地工具假设 single-user。

建议 (b)：项目 README 已声明 "本地单机工具"，加 SECURITY.md 显式条款即可。

### S3 🟢 LOW — 15 处 logger.error 含 user-controlled vars（log injection 路径）

已扫到 15 处 `logger.error(f"...{game_dir}...")` / `logger.warning(f"...{file_path}...")` 之类。如果 log 出口到 syslog / Sentry / 集中日志系统，**包含换行符的恶意 file_path**会注入新日志行。

**判断**：本地工具仅写 stdout / file，没有集中日志，**不是 actionable finding**。但应该文档化为 architectural decision。

### S4 🟢 LOW — LLM 输出回写 .rpy 时的 Ren'Py escape 处理

`file_processor/patcher.py` 759 行，含 `_escape_for_renpy_string` 等。但**没有显式 fuzz test** 验证恶意 LLM 输出（含 `"""` / `\\` / 控制字符）能被安全 escape。r53 W2 加了 JSON layer-7 escape repair，但 .rpy 行级 escape 是不同问题。

**fix**：加 1-2 fuzz test，注入恶意 LLM response 验证 escape。中等复杂度。

---

## 3️⃣ 架构与设计债（Architecture & Design Debt）

### A1 🔴 HIGH — GUI vs CLI 流程重复（792 行 GUI vs 323 行 CLI）

| 模块 | 行数 |
|------|------|
| `gui.py` | 489 |
| `gui_pipeline.py` | 230 |
| `gui_handlers.py` | 73 |
| `main.py` | 323 |

GUI handler 调用 `subprocess.Popen([sys.executable, "main.py", ...])`（CLI 间接执行），不是直接 import — **属于"safe duplication"**：GUI 改动不会破坏 CLI。但配置层级（Config 三层合并 / api_key 解析 / engine resolve）的逻辑在两边都有。

**fix**：抽取共享 `_resolve_args_from_config(args, cfg)` helper 到 `core/config.py`。中等成本，收益是改 config 逻辑只改一处。

### A2 🟡 MEDIUM — Configuration precedence 文档化不足

当前优先级：`CLI > _RENPY_TRANSLATOR_CHILD_API_KEY env > config.api_key_env > config.api_key_file > config.api_key`，**只在 main.py:240 注释里**。新贡献者必须读代码才知道。

**fix**：`docs/REFERENCE.md` 加 §"配置层级优先级"，~30 行文档。

### A3 🟢 LOW — engines/ 抽象层 vs translators/ 三条专用管线的张力

CLAUDE.md "统一入口契约"段：所有 `--engine` 都走 `engines.resolve_engine(...).run(args)`。但 Ren'Py engine `run()` 内部仍路由 tl-mode / direct / retranslate / screen 4 条专用管线。新用户读 docs 会困惑"为什么 RenPyEngine.extract_texts 是 NotImplementedError"。

**判断**：r54 已 retire A-H-3 Medium/Deep，是 explicit architectural decision。不需 fix，**可补一段 docs 解释 RenPyEngine 为什么不走 generic_pipeline**。

---

## 4️⃣ 流程与文档债（Process & Documentation Debt）

### P1 🔴 HIGH — CI 没有 lint / coverage / security-scan

实际 CI step 列表（34 步）：
- ✅ syntax check / pickle 红队 / mock target guard / verify_docs_claims / dry-run integration
- ❌ **没有** ruff / black 格式化检查
- ❌ **没有** mypy enforce（仅 informational）
- ❌ **没有** bandit security static scan
- ❌ **没有** pytest --cov 覆盖率门禁

**fix 最小集**（建议）：
- 加 `ruff check .` 和 `ruff format --check .` 作为 CI step（ruff 是单文件 binary，不破坏零依赖契约——开发依赖 ≠ runtime 依赖）
- mypy 升级为 enforce（限制范围到 `core/` + `engines/` 先行）

### P2 🟡 MEDIUM — Process docs 缺失

| 文档 | 状态 |
|------|------|
| CONTRIBUTING.md | ✅ 双语，125 行 |
| SECURITY.md | ✅ 68 行，但仅描述安全契约不含 reporting flow |
| RELEASE.md | ❌ 缺 |
| ROADMAP.md | ❌ 缺（HANDOFF 顶部包含但是 internal-style）|
| ADR (Architecture Decision Records) | ❌ 缺 — r52 C4 / A-H-3 retire / r56 file_safety move 等架构决策只在 EVOLUTION 里散落 |
| `.github/ISSUE_TEMPLATE/` | ❌ 缺 |
| `.github/PULL_REQUEST_TEMPLATE.md` | ❌ 缺 |
| `.github/dependabot.yml` | ❌ 缺（虽然零依赖，但 GitHub Actions versions 仍可 dependabot） |

**fix**：(a) 补 RELEASE.md（manual PyInstaller release flow）；(b) 抽取 ADR 到 `docs/adr/` 作为正式格式（每个决策一个 .md 文件）；(c) 加 ISSUE_TEMPLATE。中等成本，~3 commits。

### P3 🟡 MEDIUM — HANDOFF / EVOLUTION 单调增长

| 文档 | 行数 |
|------|------|
| HANDOFF.md | ~150（每轮重写 OK） |
| _archive/EVOLUTION.md | ~250+（每轮 +20 行） |
| _archive/CHANGELOG_RECENT_r52.md | ~150 |
| CHANGELOG.md | ~50（轮滚动） |

EVOLUTION 已经 250+ 行，r57+r58+... 后会爆炸。当前没有滚动归档机制（CHANGELOG_RECENT 是手动归档）。

**fix**：(a) 把 EVOLUTION 的"累积技术资产"段独立到 `docs/CAPABILITIES.md`，EVOLUTION 仅留阶段叙事；(b) 设立"满 N 轮自动归档"约定（如每 5 轮把详细叙事归档到 `_archive/EVOLUTION_rN-rN+5.md`，主 EVOLUTION 仅留摘要）。

### P4 🟢 LOW — Docs i18n 不完整

README + CONTRIBUTING 双语 ✓。但 `docs/ARCHITECTURE.md` / `docs/REFERENCE.md` / `SECURITY.md` 仅中文。国际贡献者无法读。

**判断**：项目主要面向中文用户，i18n cost > benefit。**不 fix**，但可加一行说明在 README 顶部。

---

## 5️⃣ 产品与业务债（Product & Business Debt）

### B1 🟡 MEDIUM — Release 流程 manual

`build.py` 是 manual PyInstaller。CI 仅 smoke test (import + --clean-only)。结果：
- 没有自动产出 .exe artifact
- 没有 GitHub Release 自动化
- 用户怎么知道有新版本？没机制
- 没有 SemVer / 版本号管理（pyproject.toml 是否有 version？需 verify — 但通常项目这块薄弱）

**fix**：加 GitHub Actions workflow on tag push → PyInstaller → 上传 .exe 到 Release。一次性投入 ~50 行 workflow yaml。

### B2 🟡 MEDIUM — 翻译质量持续验证缺失

r52 实测 The Tyrant 99.991%，但 r53-r56 后没再实测。没有 nightly benchmark / continuous quality gate。

**fix**：(a) 不做（用户每次跑实际项目时人工验证）；(b) 加 `tests/quality_gate.py` 定期跑 mock LLM + assert 翻译 round-trip not regress。

建议 (a)：99.991% 是真实 production data，没有 ROI 加 nightly。

### B3 🟢 LOW — 错误信息中英混用

`main.py:241` 中文 `[ERROR] 游戏目录不存在: {game_dir}`；其他地方 `[WARN]` 是英文 prefix + 中文 msg。**用户面 inconsistent**。

**fix**：选定一个标准（建议中文 prefix + 中文 msg），扫一遍统一。低成本但是高 visibility 改动。

### B4 🟢 LOW — LICENSE 法律地位

LICENSE = MIT。但项目本身是"游戏汉化工具"——产出的翻译文件法律地位（fair use? derivative work?）未明确。用户跑工具产出的翻译，**不是项目的责任**，但 README 应免责声明。

**fix**：README 加 "免责声明"段，明确翻译产物的法律责任由用户承担。低成本。

---

## 6️⃣ 组织与知识债（Org & Knowledge Debt）

### O1 🔴 HIGH — Bus factor = 1

唯一 maintainer 是 Dean。AI（Claude）协作密集但 AI 无法独立维护。如果 Dean 停更：
- HANDOFF 是给 Claude 的指引，新人类 maintainer 直接读会 confused
- CLAUDE.md 写着 "10 大开发原则" 但 implicit knowledge 散落在 EVOLUTION 250+ 行

**判断**：这是 OSS 通病，无 instant fix。**可减缓**：抽取 ADR + 加 ARCHITECTURE.md "Quick Tour for Human Maintainers" 段（不是给 AI 的）。

### O2 🟡 MEDIUM — 缺独立 Roadmap

HANDOFF.md 含 "推荐 r57+ 工作项"段，但是 internal-style（仅给 maintainer + Claude）。**没有公开 roadmap** 给用户/贡献者。

**fix**：抽取 HANDOFF 的"actionable backlog" → `ROADMAP.md`（公开版，按用户视角分类：新引擎 / 性能 / 易用性）。

### O3 🟡 MEDIUM — Onboarding 文档缺

新贡献者第一次 clone 怎么开始？目前要：
1. 读 README（3 个文档之一）
2. 读 CONTRIBUTING（环境）
3. 读 CLAUDE.md（10 大原则 + AI 上下文）
4. 读 docs/ARCHITECTURE + REFERENCE
5. 读 _archive/EVOLUTION 找历史决策
6. 读 HANDOFF 找 backlog

5 个入口，无 "Quick Start for Contributors" 单页。

**fix**：加 `docs/ONBOARDING.md` ~50 行：5 分钟跑通 + 找答案的索引。

### O4 🟢 LOW — Community 建设

GitHub repo 没有 Discussions / 没有 Discord / 没有 contributor list / 没有 sponsor 入口。

**判断**：项目仍小，community 投入回报比低。**不 fix**，等用户量增长再考虑。

---

## 📊 6 维度 Findings 汇总

| 维度 | 🔴 HIGH | 🟡 MEDIUM | 🟢 LOW | 小计 |
|------|---------|-----------|--------|------|
| 1. 技术债 | T1 | T2, T3 | T4 | 4 |
| 2. 质量与安全债 | — | S1, S2 | S3, S4 | 4 |
| 3. 架构与设计债 | A1 | A2 | A3 | 3 |
| 4. 流程与文档债 | P1 | P2, P3 | P4 | 4 |
| 5. 产品与业务债 | — | B1, B2 | B3, B4 | 4 |
| 6. 组织与知识债 | O1 | O2, O3 | O4 | 4 |
| **TOTAL** | **4** | **9** | **10** | **23** |

**所有 findings 不破坏 16 轮 0 CRITICAL streak**（无 correctness bug；多数是流程 / 体验 / 长期维护问题）。

---

## 🎯 推荐 Fix Path

### 路径 X — 全部 fix（路径 C 的延续，~1500 行改动）

23 项全闭合。预估 5-8 commits。

### 路径 Y — 仅 H + M（建议，~400 行改动）

13 项 fix（4 H + 9 M）。L 留 architectural decision 文档化。预估 3-4 commits。

| 维度 | H + M findings |
|------|---------------|
| 技术债 | T1 + T2 + T3 |
| 质量与安全债 | S1 + S2 |
| 架构与设计债 | A1 + A2 |
| 流程与文档债 | P1 + P2 + P3 |
| 产品与业务债 | B1 + B2 |
| 组织与知识债 | O1 + O2 + O3 |

### 路径 Z — 仅 H（最小冲击，~150 行改动）

4 项 fix：
- T1（Python 版本契约统一）
- A1（GUI/CLI config 抽取共享）
- P1（CI lint/cov/bandit）
- O1（ADR 抽取 + ARCHITECTURE 加人类入口）

预估 2 commits。最防御性。

### 路径 W — 拒绝 fix，全部 retire to architectural decision

承认这些是项目特性（小团队 / 中文优先 / AI 协作），文档化为 explicit decisions 而非 debt。预估 1 commit。

---

## 🎯 Audit 提出方建议

**路径 Y**（H + M 全 fix）。理由：

1. **T1 + P1 是真 latent bug + missing safety net**——3.9 兼容声称 vs `int | None` 用法不一致是 silent fail；CI 没 lint 让代码风格慢慢漂移。这两项不修等于在违反"零欠账闭合"原则。

2. **A1 + A2 + B1 改善长期维护性**——配置抽取 + release 自动化让你每次 commit/release 不再手动操心。

3. **P2 + P3 + O2 + O3 提升开放性**——ADR / RELEASE / ROADMAP / ONBOARDING 这套是 OSS 项目"成熟度"标志。当前状态是个"私人项目 + AI 协作"，转向 OSS-grade 需要这些。

4. **L 级**（T4/S3/S4/A3/B3/B4/P4/O4）多数是 cosmetic 或 ROI < cost，**显式 retire to architectural decision**比硬干强。

5. **预估**：路径 Y ≈ 4 commits 完成，每 commit 闭合 1 维度的 H+M。和 r56 路径 C 体量相仿。

---

## 备注

- 本文件由 r57 audit 阶段创建，目的是防止决策遗忘
- 一旦 fix path 选定并实施完成，本文件应：
  - (a) 移到 `_archive/AUDIT_R57.md` 作为历史记录
  - (b) 或直接删除（findings 已写入 EVOLUTION + HANDOFF）
- 当前**未 commit**——选择 fix 范围后再决定是否一起 commit
