# HANDOFF — Round 53 末 → Round 54 起点

<!-- VERIFIED-CLAIMS-START -->
tests_total: 467
test_files: 32
ci_steps: 34
assertion_points: 593
<!-- VERIFIED-CLAIMS-END -->

> **上方 fenced 块是声明数字的唯一位置**。其他文档（`CLAUDE.md` / `.cursorrules` / `CHANGELOG.md` / `_archive/EVOLUTION.md` / `README.md` 等）只能引用这些数字，**不能重新声明**。`scripts/verify_docs_claims.py` 在 pre-commit hook 自动检查，drift fails the commit。
>
> 字段定义（由 `verify_docs_claims.py` 静态推导）：
>
> - `tests_total` — `tests/test_*.py` + `tests/smoke_test.py` 中所有 top-level `def test_*` / `async def test_*` 的 AST 计数
> - `test_files` — `tests/test_*.py` + `tests/smoke_test.py` 文件数
> - `ci_steps` — `.github/workflows/test.yml` 中 `jobs.test.steps` 长度
> - `assertion_points` — `tests_total + sum((N assertions))`，第二项从含 `self-test` label 的 CI step 名称解析（当前 `tl_parser` 75 + `screen` 51 = 126）
>
> `--full` 模式额外实跑全部 CI `Run *` step 作 sanity gate。

---

## 状态一句话

纯 Python 零依赖**zh-only**游戏汉化工具。**Round 53 完成 retry 阶段并发化 + JSON mis-escape 鲁棒化 + LLM ID drift 检测 + 6 个监控项重新评估**（W1 retry ThreadPoolExecutor / W2 layer-7 escape-fix / W3 layer-6 ID drift / W4 direct-mode English-only 文档化 / 监控 #1 pickle 红队 verified safe / 监控 #2 HTTP 64KB 精度偏差降至 1B / 监控 #3+#5+#6 retire to architectural decision / 监控 #4 symlink CLI warning + `--allow-symlink`）。**连续 13 轮 0 CRITICAL correctness**（r35-r53）。

## 同步状态

- r53 实施完成（W1-W4 + 6 监控项），全量 `tests/test_all.py` 0 fail
- 本地未 push（按 NEVER push 政策保留 commit 决策给用户）
- pre-commit hook 已激活（`git config core.hooksPath = .git-hooks`）
- 4 件套 + r52 C1 push-status drift check 自动 enforce：py_compile + 800 行 cap + meta-runner + `verify_docs_claims --fast` (含 push-status check)
- Git remote: `https://github.com/Dean20030514/Multi-Engine-Game-Translator.git`

## 架构健康度（核心维度）

| 维度 | 状态 |
|------|------|
| 大文件（> 800 行） | ✅ 全 .py < 800（pre-commit + verify_docs_claims --fast 自动 enforce） |
| 数据完整性 | ✅ TranslationDB 线程安全（RLock）+ 原子写入（os.replace）+ schema v2 partial backfill |
| 反序列化安全 | ✅ 3 处 pickle 全白名单（`core/pickle_safe.py` + rpyc Tier 1+2 + rpa_unpacker）+ **r53 红队 audit 8/8 PASS**（os.system / Popen / eval / exec / `_codecs.encode` / `copyreg._reconstructor` GadgetChain 全部 blocked） |
| 插件沙箱 | ✅ **Subprocess 强制沙箱**（r52 BREAKING retire importlib）+ 启动期 readiness probe + 三通道防护（stdout 50M chars + stderr 10K + stdin lifecycle） |
| 目标语言 | ✅ **zh 简体中文 only**（r52 C4 BREAKING：r35-r48 多目标语言 5 层 contract + `core/lang_config.py` + `--target-lang` + translation_db v2 schema + runtime-hook v2 schema 全部 retire；存量 v2 DB 用 `scripts/migrate_db_v2_to_v1.py` 迁移） |
| OOM 防护 | ✅ 23/23 user-facing path-stat + 26 sites / 12 modules TOCTOU MITIGATED via `core.file_safety` 共享 helper |
| HTTP 响应体 cap | ✅ **r53 监控 #2: 精度偏差 65535 B → 1 B**（`read_bounded` chunk size 改为 `min(_READ_CHUNK_SIZE, limit - total + 1)`） |
| Mock target stale trap | ✅ CI grep step 兜底（防 r48 trap CLASS 复发；r50 C4 filter 放宽到 `file_safety` 兼容 qualified form；r51 audit-tail 加第三级 `test_repo_rename_consistency` filter 豁免 documentation-only 文件 self-trip） |
| Repo rename consistency | ✅ Round 51 加 4 contract tests 钉自身 repo URL refs + logger namespace + 上游归属反向 exhaustiveness |
| Retry stage 并发 | ✅ **r53 W1**: `translators/_tl_retry.py` ThreadPoolExecutor + per-chunk `[TL-RETRY n/N]` log + 自适应 chunk size (>50→10, ≤50→5) |
| LLM ID drift 检测 | ✅ **r53 W3 layer 6**: `detect_id_drift()` 在主 stage + retry stage 各注入；symmetric-difference > 10% 触发 `[W3-DRIFT]` warn（observation only，不 abort） |
| LLM JSON 容错 | ✅ **r53 W2 layer 7**: `_repair_unescaped_quotes_in_strings` char-walker 修字符串值内未 escape `"`；6 级结构降级链不变 |
| 模块分层 | ✅ deferred import 保 layering（`file_processor` 不在 module load 时 import `core`） |
| docs claim drift | ✅ 4 项 prevention 自动化（pre-commit hook + `verify_docs_claims --fast`/`--full` + `VERIFIED-CLAIMS` 单一声称源） |
| debt closure | ✅ Round 50 起规则强制：所有 findings 同轮 fix，零 deferred；r51 / r52 / r53 各 1 次执行验证有效 |
| 累计审计 | ✅ 连续 13 轮 0 CRITICAL correctness（r35-r53） |

## 推荐的 Round 54+ 工作项

> Round 53 完成时**零 deferred actionable items**（W1-W4 全完成 + 6 监控项各自闭合或 retire 到 architectural decision）。下列均为 r54+ 候选新工作。

### 🟠 需真实 API + 游戏（独立一轮）

1. **A-H-3 Medium**：adapter 让 Ren'Py 走 generic_pipeline 6 阶段（refactor + byte-identical 输出 baseline 验证）
2. **A-H-3 Deep**：完全退役 DialogueEntry
3. **RPG Maker Plugin Commands (code 356)**：需真实 MV/MZ 游戏样本
4. **加密 RPA / RGSS 归档**：需加密样本

### 🟡 引擎路线图（详见 [docs/REFERENCE.md §13.2](docs/REFERENCE.md)）

- P1: RPG Maker VX/Ace / Wolf RPG Editor / Godot
- P2: Unity (XUnity) / Kirikiri 2/Z / TyranoBuilder
- P3: Unreal Engine / HTML5

### ⚫ 监控项（informational watchlist，not actionable debt）

> r53 末重新评估：6 项中 5 项 retire 到 architectural decision（已 verified safe 或本地工具威胁模型不适用），1 项升级为 mitigation。

- ~~Pickle 白名单 `_codecs.encode` / `copyreg._reconstructor` 理论链式攻击~~ — **r53 监控 #1 verified safe**：`tests/test_pickle_safe_redteam.py` 8/8 红队 payload 全 blocked（直接调用 gadget + chain GadgetChain + whitelist 边界）；`_codecs.encode` 仅产生 inert bytes/str，`_reconstructor` 在 base class resolve 阶段被 SafeUnpickler 拒绝
- ~~HTTP 响应体 64 KB 精度偏差~~ — **r53 监控 #2 mitigated**：`core/http_pool.py::read_bounded` chunk size 改为 `min(_READ_CHUNK_SIZE, limit - total + 1)`，最大精度偏差从 65535 B 降至 1 B
- ~~TOCTOU fstat 自身 race 窗口~~ — **r53 监控 #3 retire to architectural decision**：microsecond 级 OS-atomic 边界，进一步 narrow 依赖 OS 实现细节，无 actionable improvement path
- ~~Symlink path-swap TOCTOU~~ — **r53 监控 #4 mitigated**：`main.py::_maybe_warn_on_symlink` 在 `--game-dir` / `--config` 是 symlink 时 warn；`--allow-symlink` 抑制（NAS / 挂载场景）；本地 single-user 工具无 realistic exploit vector，warning 仅作审计提示
- ~~Logger namespace 行为契约~~ — **r53 监控 #5 retire to architectural decision**：r51 4 contract tests pin 17 sites `getLogger("multi_engine_translator")` 已充分；如未来引入 logging filter / sink / metric pipeline，需 reconsider
- ~~GUI 自动化~~ — **r53 监控 #6 maintained as architectural decision**：tkinter 跨平台 headless 需 Xvfb (Linux only) 或 `pyvirtualdisplay`（违反零依赖契约）；ROI 低 + 跨平台覆盖不全；保留为 informational watchlist，如未来引入纯 stdlib 的 GUI mock 框架可重新评估

### ✅ 已 retired / 完成（r53 闭合）

- ~~**W1 retry 单线程 + 零 logging**~~ — **r53 W1 完成**（`translators/_tl_retry.py` 174 行新模块 + ThreadPoolExecutor + per-chunk log + 自适应 chunk size + 17 单元测试 PASS）
- ~~**W2 LLM JSON mis-escape**~~ — **r53 W2 完成**（`core/api_client.py` layer-7 char-walker repair + 5 单元测试 PASS）
- ~~**W3 fallback 链 audit + ID drift detection**~~ — **r53 W3 完成**（5 层 fallback 表述修正 + layer-6 `detect_id_drift()` 主 stage + retry stage 各注入；HANDOFF 历史 "4 层"表述 stale，实际 r31 起就是 5 层 precise→strip→token→escape→tagstripped）
- ~~**W4 direct-mode source-language awareness**~~ — **r53 W4 完成**（路径 b：启动 INFO log + `MIN_ENGLISH_CHARS_FOR_UNTRANSLATED` 常量 docstring + README §source language assumption + CLAUDE.md 已知限制段；不加 `--source-lang` CLI 避免功能蔓延）
- ~~6 个监控项重新评估~~ — **r53 完成**（见上"监控项"段，5 项 retire / 1 项 mitigation）

---

## 关键文件路径速查

| 类别 | 路径 |
|------|------|
| AI 全局上下文 | `CLAUDE.md` / `.cursorrules`（byte-identical） |
| 本次交接 | `HANDOFF.md`（本文件） |
| 用户面文档 | `README.md`（中英双语） |
| 变更日志 | `CHANGELOG.md`（极简入口）+ `_archive/EVOLUTION.md`（r1-r53） |
| 全量历史 | `_archive/CHANGELOG_FULL.md` + `_archive/CHANGELOG_RECENT_r52.md`（r48-r52 详细） |
| 入口 | `main.py` / `gui.py`（mixin） / `one_click_pipeline.py` |
| 引擎抽象 | `engines/{engine_base, engine_detector, generic_pipeline, renpy_engine, rpgmaker_engine, csv_engine}.py` |
| 核心 | `core/{api_client, api_plugin, config, glossary, prompts, translation_db, translation_utils, http_pool, pickle_safe, font_patch, runtime_hook_emitter, file_safety}.py`（r52 C4：lang_config 已删除） |
| 流水线 | `pipeline/{helpers, gate, stages}.py` |
| 翻译子模块 | `translators/{direct, tl_mode, retranslator, screen, tl_parser, renpy_text_utils}.py` + 7 私有子模块（含 r53 新 `_tl_retry.py`） |
| 测试 | `tests/test_all.py` meta-runner + 32 独立 suites（含 r53 新加 `test_tl_retry.py` + `test_pickle_safe_redteam.py`） |
| docs | `docs/ARCHITECTURE.md`（架构 + 数据流 + 校验链 + 引擎指南 + 测试体系）+ `docs/REFERENCE.md`（常量 + 错误码 + 路线图） |
| CI | `.github/workflows/test.yml`（双 OS matrix × 3 Python = 6 jobs；step 数见 VERIFIED-CLAIMS）+ `scripts/verify_workflow.py` |
| 开发者工具 | `.gitattributes` + `.gitignore` + `build.py --clean-only` + `.git-hooks/pre-commit` + `scripts/{install_hooks.sh, verify_workflow.py, verify_docs_claims.py, migrate_db_v2_to_v1.py}` |

---

## 下次新对话接手指南

**必读顺序**（上下文从零开始）：

1. **本文件** — 当前状态 + 推荐工作项 + 文件路径
2. **`CLAUDE.md`** — 项目身份 + 10 大开发原则 + 模块图（zh-only since r52 C4）
3. **`docs/ARCHITECTURE.md`** + **`docs/REFERENCE.md`** — 架构与常量
4. **（按需）** `_archive/EVOLUTION.md` — 历史决策（含 r53 段）
5. **（按需）** `_archive/CHANGELOG_RECENT_r52.md` — 最近 5 轮（r48-r52）详细

**Round 54 关键约束**：
- audit findings 必须**同轮 fix，no tier exemption**（r50 起 written + enforced；r51 / r52 / r53 各执行 1 次有效）
- 数字声称只在本文件 `VERIFIED-CLAIMS` 块声明
- 修改 `CLAUDE.md` 必须同步 `.cursorrules`
- 修改 logger namespace / repo URL self-references 必须保持 `tests/test_repo_rename_consistency.py` 4 contract tests 全 PASS（r51 加固）
- 6 处 anonymousException 上游归属永远不能被任何 sed/refactor 误删
- **目标语言固定 zh**（r52 C4 BREAKING）— 任何 multi-target / lang_config / target-lang 重新引入必须先 plan-first 撤销 r52 C4
- **插件强制 subprocess sandbox**（r52 C3 BREAKING）— 任何 importlib in-process loader 重新引入必须先 plan-first 撤销 r52 C3
- **`tl_mode.py` retry 路径必须保持并发**（r53 W1）— 任何 sequential retry 重新引入必须先 plan-first
- **LLM ID drift detection 必须保留 layer-6**（r53 W3）— 任何主 stage / retry stage 移除 `detect_id_drift()` 必须先 plan-first
- **Pickle 白名单不得放宽**（r53 监控 #1 verified）— 任何向 `_SAFE_BUILTINS` / `_SAFE_COLLECTIONS` / `_SAFE_CODECS` / `_SAFE_COPYREG` 添加新 entry 必须先跑红队 audit
- pre-commit hook 已激活，会自动 enforce file-size cap + drift check + r52 C1 push-status drift check
