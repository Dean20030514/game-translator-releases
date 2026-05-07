# EVOLUTION rounds r56-r60 (archived from main EVOLUTION.md at r60)

> **归档由来**：r58 P3 hard contract #15 约定每 5 轮把"阶段 N-4 → 阶段 N" 5 段完整叙事抽离到 `_archive/EVOLUTION_rN-4_rN.md`，主 EVOLUTION.md 仅保留摘要 + 阶段表格行。**r60 是该 contract 的首次执行**。
>
> **本归档**包含 r56-r60 5 阶段的**完整原文叙事**，从主 [`EVOLUTION.md`](EVOLUTION.md) 抽出后保留作 reference。后续 round 如需查阅 r56-r60 详细内容，看本文件；主 EVOLUTION.md 仅留 5 行精简摘要。
>
> **r66 retire 注解**：本文叙事中提到的 `docs/adr/` 路径 / `[ADR NNNN]` 链接 / `AUDIT_R57.md` 在 r66 已**全部删除**（用户决策）。叙事保留是为历史完整；当前架构契约请直接看 [`CLAUDE.md`](../CLAUDE.md) "维护规则"段 hard contracts 列表。
>
> **下一次归档**触发 **r65**：归档 r61-r65 → `_archive/EVOLUTION_r61_r65.md`。
>
> **关联 commits**：
> - r56: `a997ee2` `refactor(round-56): full audit + 8 fixes (path C closure)`
> - r57: `d03c249` `refactor(round-57): 6-dimension debt audit + tech & quality/security closure`
> - r58: `a9da1cd` `refactor(round-58): A1-A3 + P1-P4 audit closures (arch + process docs)`
> - r59: `9a89964` `docs(round-59): close AUDIT_R57.md — product/business + org/knowledge dimensions`
> - r60: 本归档所在 commit

---

## 阶段十五（r56）— 全面深度审计 + 8 项 fix（路径 C）+ 16th 0-CRITICAL Streak

8 phases，纯优化轮无新功能：

- **本轮触发**：r55 末用户要求"全面且深度的检查一遍"。8 维度 audit (correctness / security / performance / code quality / test coverage / docs drift / architecture / concurrency) 收集 11 findings (3 HIGH / 3 MEDIUM / 5 LOW)；用户决策路径 C 全部 fix（含 L 级别 cosmetic 项）。
- **审计标准**：以 r35-r55 项目 audit 框架 + r52 起"减法 + 聚焦"原则。所有 fix 同轮闭合（CLAUDE.md 第 10 原则零欠账闭合）。
- **H1 — `core/api_client.py` 5 死 import 清理**：`atexit` / `importlib.util` / `sys` 是 r52 C3 BREAKING retire `_load_custom_engine` (importlib in-process loader) 后清理不彻底的残留；`Optional` / `Any` 是 typing 导入但无实际使用。grep verify 0 调用。
- **H2 — logger sites 17 → 24 docs drift**：r51 加固时数字 17，r52-r55 新模块（unity_xunity / _tl_retry / 等）自然增长但 docs 未同步。r56 把"17 sites"硬编码改为"覆盖所有 production 模块（r56 末实测 24 sites — contract 是覆盖而非定值）"软描述，HANDOFF / CLAUDE.md / .cursorrules / docs/REFERENCE.md / EVOLUTION 全部同步。
- **H3 — `engines/unity_xunity.py` r55 残留 `field` 死 import**：r55 我自己引入的死代码，`_ParsedLine` dataclass 全是简单默认值不需 `field(default_factory=...)`。
- **M1 — Unity XUnity regex backref placeholder protection**（用户 Q3 选 (a)）：`UNITY_XUNITY_PROFILE.placeholder_patterns` 加 9 个 patterns 保护 regex 元字符（`\d` `\D` `\w` `\W` `\s` `\S` `\b` `\B` `\[1-9]`）。当 regex_rule pending 时 pattern 作为 original 喂 LLM，`generic_pipeline.protect_placeholders` 把 backref 替换为 `__RENPY_PH_*__` 占位符，restore 时还原。`tests/test_unity_xunity_engine.py` +2 测试覆盖（profile 编译 + protect/restore round-trip）。
- **M2 — `core/file_safety.py` → `safety/file_safety.py` 顶层独立 package**（用户 Q3 选 (b)）：`file_processor.checker` 顶层 import `core.file_safety` 与 CLAUDE.md 模块图描述"`file_processor` 不在 module load 时 import `core`"冲突。把 helper 移出 `core/` 到顶层 `safety/`：18 production .py imports 迁移；`safety/__init__.py` re-export `check_fstat_size`；3 测试 mock target 迁移；CI workflow `Mock target consistency check` step 文档更新（**关键**：fragment match `grep -v "file_safety"` 兼容两种路径，r48 stale mock trap CLASS 仍生效，无需重写 CI guard 逻辑）；`tests/test_repo_rename_consistency.py` 文档更新；CLAUDE.md 模块图调整。
- **M3 — `_translate_one_tl_chunk` 函数内 import → 顶层**：r53 W3 加 ID drift detection 时函数内 `from translators._tl_retry import detect_id_drift, _expected_id_set` 是循环 import 防御性写法（每次 chunk 翻译都 import 一次，sys.modules 缓存让开销很小但与项目 idiomatic style 不一致）。实测 `_tl_retry` 不依赖 `tl_mode`，无循环，提到模块顶层。
- **L1 — production print() → logger.info()**（用户指示：仅 build.py 保留 print，其他全改）：4 个 translators 模块 print 调用迁移 — `screen.py` (12 处) / `tl_parser.py` (15 处) / `_tl_nvl_fix.py` (1 处) / `_tl_postprocess.py` (1 处)，共 29 处。3 个文件新增 `import logging` + `logger = logging.getLogger("multi_engine_translator")` 绑定。`pipeline/*` 和 `one_click_pipeline.py` 已用 `_print()` wrapper（pipeline/helpers.py L37：`def _print(msg): logger.info(msg)`），实质已 logger，audit 时 `grep print(` 假阳性。
- **L2 — hard contract 计数术语统一**：参见 H2，硬编码数字改软描述。
- **数字增量**：tests_total 483 → 485 (+2 r56 M1 backref tests); test_files 33 unchanged; ci_steps 34 unchanged; assertion_points 609 → 611 (+2)。
- **VERIFIED-CLAIMS / .cursorrules byte-identical / pre-commit 4 件套** 全部 OK。
- **13 hard contracts 不变**（无新约束加入）。

**连续 16 轮 0 CRITICAL correctness 保持**（r35-r56）。

---

## 阶段十六（r57）— 6 维度深度债务审计 + 技术债 / 质量与安全债全闭合 + 17th 0-CRITICAL Streak

6 phases，覆盖 r56 末用户提出的"还有没有其他的技术债 / 质量与安全债 / 架构与设计债 / 流程与文档债 / 产品与业务债 / 组织与知识债"6 大维度审计：

- **本轮触发**：r56 已完成代码卫生面 audit（11 findings 全 fix）；用户提出更深层 6 维度审计请求。本轮先扫描 6 维度共 23 findings（4 HIGH / 9 MEDIUM / 10 LOW），然后**优先推进维度 1 (技术债 T1-T4) + 维度 2 (质量与安全债 S1-S4) 共 8 项**。剩余 4 维度（A1-A3 / P1-P4 / B1-B4 / O1-O4）保留给 r58+。审计全程留底 `AUDIT_R57.md`（项目根目录）。
- **T1 — Python 版本契约统一**（HIGH）：`pyproject.toml requires-python = ">=3.10"`；CI matrix `[3.9, 3.12, 3.13]` → `[3.10, 3.12, 3.13]`；CLAUDE.md 模块图 + README 中英 + CONTRIBUTING 中英 全部 "Python ≥ 3.9" → "Python ≥ 3.10"。根因：项目 7 个文件用 PEP 604 `int \| None` 语法，运行时仅 3.10+ 支持；3.9 仅 `from __future__ import annotations` 才能 lazy eval — 任何 missing future import 的文件在 3.9 都 ImportError，是 silent latent bug。
- **T2 — Mypy informational → enforce**（MEDIUM）：CI step 移除 `\|\| true` + `continue-on-error: true`；6 文件 scope (`core/translation_utils.py / core/config.py / file_processor/ / core/api_client.py / core/glossary.py / core/translation_db.py`) 实测 32 errors 全 fix：
  - 21 `core/api_plugin.py` `Optional[Popen[str]]` access — 加 `# type: ignore[union-attr]` 标记 runtime-safe（self._proc 仅 init 期短暂 None）
  - 2 `core/translation_db.py` 加 `Optional` typing import
  - 6 `file_processor/splitter.py` chunks 加 `list[dict[str, Any]]` type hint + `read_file` 签名 `object` → `Union[str, Path]`
  - 1 `file_processor/checker.py` `rv` 加 `tuple[str, list]` annotation
  - 2 `core/api_client.py::RateLimiter.acquire` 重命名 minute_counts 循环变量 (k → m_key) 避免与上面 second_counts int-keyed 循环冲突的 mypy 类型推断
- **T3 — Complex fixture 集成测试**（MEDIUM）：`tests/test_complex_fixture.py` 新建 — synthetic 复杂 .rpy fixture（6 dialogue 块覆盖 nvl_clear / nvl_narrator 块 / multi-line `\\n` 内嵌 say / `{i}` `{b}` `{color=#fa0}` `{size=+4}` 标签 / `[name]` `[item_count]` 变量 / 转义引号 `\\\"...\\\"` / SAZMOD 模组路径 + 3 string 块覆盖 `Save` `Load` 嵌套标签 New Game）+ 2 集成测试（scan extracts 6+3 entries / fill round-trip 保留所有注释空行 + 6 dialogue + 3 strings 全部 fill）。补 `_TL_EMPTY_FIXTURE`（4 简单 entries）与 r52 实测 74098 entries 的 fixture 复杂度差距。
- **T4 — `tools/` 散乱无共享 base** retire to architectural decision（LOW）：CLAUDE.md "已知限制" 段记录。15 CLI tool 各自 entry 是项目第 8 原则"最小改动"接受的代价；如未来需批量 cross-tool feature（如 `--dry-run` for all）再 reconsider。
- **S1 — `.gitignore` secret patterns**（MEDIUM）：加 `.env` / `.env.*` / `*.key` / `*.pem` / `api_keys.json` / `secrets.json`（`renpy_translate.json` + `*.bak` 已存在）。defense-in-depth 防止开发者 `git add .` 误传 API key。
- **S2 — `_sanitize_user_path` path traversal 防护**（MEDIUM）：`main.py` 新加 helper + `_FORBIDDEN_PATH_PREFIXES` 元组（POSIX `/etc/` `/sys/` `/proc/` `/dev/` `/root/` `/boot/` `/var/log/` `/var/run/` + Windows `c:/windows/` `c:/program files/` `c:/program files (x86)/` `c:/programdata/` `c:/system volume information/` + `/etc/passwd` `/etc/shadow`）。main() 调 sanitize args.game_dir 和 args.config（如非空）。3 测试覆盖（forbidden resolved path mock / Windows System32 mock / legitimate path passthrough）。本地 single-user 工具威胁模型不变，主要 protect 多用户共享环境（CI runner / 教学 / 实验室）。
- **S3 — Log injection** retire to architectural decision（LOW）：CLAUDE.md "已知限制" 段记录。15 处 `logger.error(f"...{user_var}...")`，本地工具仅写 stdout 无集中日志（syslog / Sentry），不构成 actionable；如未来引入需 sanitize user vars 中的换行符。
- **S4 — `.rpy` escape fuzz 测试**（LOW，但用户选 fix）：`tests/test_file_processor.py` 加 2 测试覆盖 `_escape_for_renpy_string`：fuzz with 12 adversarial LLM payloads（bare `"` / `\\` / `\\"` / `\\\\` / `"""` / 混合 `"` 和 `\\` / 三种行尾混排 / 1000+ 字符 / NUL char / tab / 非 ASCII + quotes / 空字符串）+ property-based 不变量断言（escape 后所有 `"` 必有奇数前导反斜杠 / 无裸 `\\r` 泄漏 / 函数不崩）+ idempotence 测试（safe input 不被错误重转义）。
- **数字增量**：tests_total 485 → 492 (+7: 3 S2 + 2 S4 + 2 T3); test_files 33 → 34 (+1: `test_complex_fixture.py`); ci_steps 34 unchanged; assertion_points 611 → 618 (+7)。
- **13 hard contracts → 16**（CLAUDE.md / .cursorrules / HANDOFF Round 58 关键约束）：
  - **mypy enforce contract**：6 文件 scope 必须保持 0 errors；新文件加入 scope 前必须先 mypy clean
  - **Python ≥ 3.10 contract**：retreating to 3.9 需 plan-first（PEP 604 已广泛使用）
  - **Path traversal contract**：`_FORBIDDEN_PATH_PREFIXES` 不可放宽，任何新 user-supplied path 入口经 `_sanitize_user_path`
- **审计留底**：`AUDIT_R57.md`（项目根目录）保留完整 6 维度 23 findings 报告 + 4 fix 路径选择（X / Y / Z / W），方便后续轮 reference。

**连续 17 轮 0 CRITICAL correctness 保持**（r35-r57）。

---

## 阶段十七（r58）— 架构设计 + 流程文档全闭合 + 18th 0-CRITICAL Streak

5 phases，覆盖 r57 末 [`AUDIT_R57.md`](../AUDIT_R57.md) 6 维度审计的维度 3 (架构与设计 A1-A3) + 维度 4 (流程与文档 P1-P4) 共 8 项 fix（不算 P 维度内自然闭合的子项；维度 5 产品业务 + 维度 6 组织知识保留给 r59+）。

- **A1 — `_resolve_args_from_config` 共享 helper 抽取**：`main.py::main()` L249-266 inline 三层合并代码（CLI > config file > defaults）抽到 `core/config.py::resolve_args_from_config(args, cfg)`。helper 接受 argparse Namespace + Config，按文档化的优先级填充字段（包括 r52 C4 BREAKING 硬编码 target_lang="zh"）。GUI / one-click pipeline / 未来 entry 共享同一逻辑，改 config 只需改 helper 一处。+2 单元测试（fills_defaults 验证 4 fields / target_lang_hardcoded_zh 验证即使 config 写 "ja" 也强制 zh）。
- **A2 — 配置层级优先级文档化**：`docs/REFERENCE.md §7a` 新加 — 6 层 API key fallback 优先级表（CLI > 子进程 env > config api_key_env > config api_key_file > config api_key 明文 > argparse default）+ 三层 config 合并逻辑说明 + 引用 r58 A1 helper 路径。
- **A3 — RenPyEngine 不走 generic_pipeline 文档化**：`docs/REFERENCE.md §13.2.1` 新加 6 项对比表（提取单位 / 分块策略 / 回写精度 / Retry 阶段 / Fallback 链 / LLM mis-escape）+ 4 条 r54 retire A-H-3 Medium/Deep 的核心理由 + 交叉引用 ADR 0004 / EVOLUTION 阶段十三。解决新工程师读 `engines/renpy_engine.py` `extract_texts` 抛 `NotImplementedError` 的困惑。
- **P1 — CI 加 ruff lint + format + mypy scope 扩大**：(a) `.github/workflows/test.yml` 加 `ruff check .` + `ruff format --check .` 两个 CI step（ruff 是 dev-time tool，不破坏零依赖契约 — ADR 0001 仍 hold；CI 自己 `pip install ruff`）；(b) `pyproject.toml` 加 `[tool.ruff]` 配置（target-version py310 + line-length 100 + extend-exclude `_archive` `tests/artifacts` + select E/F/W + extend-ignore E402 `# 项目惯例 sys.path.insert before imports` / E501 `# 100-char informational, bulk-rewrap out of scope` / F841 `# 12 sites kept as debug placeholders, future rounds may revisit`）+ format quote-style "double" + indent-style "space"；(c) **一次性 ruff format .**：99 files reformatted（baseline 立起；新 PR `ruff format --check` 必须保持 0 diff）；(d) **`ruff check --fix .`**：132 errors auto-fixed（主要 F401 unused import 91 + F541 f-string-without-placeholder 25 + E401 multiple imports on one line 17 + F811 redefinition of unused 9）；(e) mypy CI step 加第二行 invocation：`mypy --ignore-missing-imports --follow-imports=silent engines/ safety/`。`--follow-imports=silent` 让 transitive translators/ imports 不 gate（translators/ 仍有 ~20 mypy errors 因为 DialogueEntry/StringEntry isinstance branches 让 mypy 类型推断失败，留 follow-up）。原 6 文件 scope 0 errors 仍保持。
- **P2 — Process docs 大补**：(a) [`RELEASE.md`](../RELEASE.md) — 165 行：版本号管理 (SemVer) + 手动发布 6 步流程（pre-release 检查 / bump version / tag+push / PyInstaller / GitHub Release / 验证 artifact）+ 自动化 GitHub Actions tag-trigger workflow 候选（~50 行 yaml 设计）；(b) [`ROADMAP.md`](../ROADMAP.md) — 公开版（用户/贡献者视角，与 internal HANDOFF backlog 区分）；当前能力 / 短期 ROI 排序 / 中期方向 / 长期愿景（用户驱动）/ 已 retire 完整列表；(c) [`docs/adr/`](../docs/adr/) 框架 — README 索引（5 ADR + 模板 + 何时写 / 何时不写指南）+ 5 份 ADR 内容：0001 zero-third-party-dependencies (r1) / 0002 zh-only-target-language (r52 C4 BREAKING) / 0003 subprocess-sandbox-only-plugin (r52 C3 BREAKING) / 0004 renpy-stays-on-dedicated-pipelines (r54 retire A-H-3) / 0005 safety-as-toplevel-package (r56 M2)；每 ADR ~70 行（背景 / 考虑方案 / 决策 / 后果 / 关联）；(d) [`.github/ISSUE_TEMPLATE/bug_report.md`](../.github/ISSUE_TEMPLATE/bug_report.md) + [`feature_request.md`](../.github/ISSUE_TEMPLATE/feature_request.md) + `config.yml`（禁 blank issue + 引导 SECURITY advisory + Discussions Q&A）；feature_request 含 hard contracts 触及 checklist；(e) [`.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md) — 改动类型 (含 BREAKING 标记) / 验证 6 项 checklist / hard contracts 检查 / docs sync 5 项 checklist / 测试覆盖；(f) [`.github/dependabot.yml`](../.github/dependabot.yml) — github-actions ecosystem monthly + comment 解释为啥**没有 pip ecosystem**（ADR 0001 零依赖契约）。
- **P3 — EVOLUTION 滚动归档约定**：CLAUDE.md 加"## 文档归档节奏"段（在"自动化与 drift 防御"和"维护规则"段之间）。约定：每 5 轮（r60 / r65 / r70 / ...）触发一次归档；操作 4 步（抽 5 阶段叙事到 `_archive/EVOLUTION_rN-4_rN.md` / 主 EVOLUTION 留摘要 / 索引更新 / `wc -l` 验证主文件减 ≥ 100 行）；不归档项（阶段表格 / 累积技术资产 / 设计原则演进）；下次触发 **r60**（当前 r58 后再 2 轮）。
- **P4 — README 顶部 i18n 说明**：明确告诉国际贡献者 README + CONTRIBUTING 双语；其他 docs 仅中文（项目主要面向中文用户）；in-repo 代码 / 注释 / commit 仍英文（global CLAUDE.md 通信规则）。
- **800-line cap split**（ruff format 让 2 测试文件越界，r58 同轮 fix）：
  - `tests/test_translators.py` 832 → 654 行：拆 6 个 main.py CLI 测试到新 [`tests/test_main_cli.py`](../tests/test_main_cli.py) 221 行（test_w_monitor4_* 3 个 + test_w_round57_s2_* 3 个）— 这些测试 exercise `main._maybe_warn_on_symlink` / `main._sanitize_user_path`，跟 translators/ 无关，自然拆点
  - `tests/test_file_safety.py` 807 → 798 行：精简模块顶部 docstring（保留所有 21 测试逻辑）
- **数字增量**：tests_total 492 → 494 (+2: r58 A1); test_files 34 → 35 (+1: `test_main_cli.py`); ci_steps 34 → 36 (+2: ruff check + ruff format --check); assertion_points 618 → 620 (+2)。
- **2 个新 hard contracts** (HANDOFF Round 59 关键约束)：
  - **CI ruff lint/format 门禁**：任何新 PR 必须 `ruff check .` + `ruff format --check .` 全过；`pyproject.toml [tool.ruff]` extend-ignore 列表不得放宽
  - **EVOLUTION 滚动归档**：r60 触发首次（每 5 轮一次）；归档时主 EVOLUTION 减 ≥ 100 行
- **维度 5/6 留 r59+**：B1-B4（产品业务）+ O1-O4（组织知识）共 8 项保留给后续。

**连续 18 轮 0 CRITICAL correctness 保持**（r35-r58）。

---

## 阶段十八（r59）— 产品业务 + 组织知识维度全闭合 + 19th 0-CRITICAL Streak + AUDIT_R57.md 收尾

6 phases（quick wins + B1 release.yml + ARCHITECTURE Quick Tour + ONBOARDING + B3 message + final docs sync），完成 [`AUDIT_R57.md`](../AUDIT_R57.md) 6 维度 23 findings 全闭合（r57: T1-T4 + S1-S4 / r58: A1-A3 + P1-P4 / **r59: B1-B4 + O1-O4**）。

- **B1 — Release 自动化 GitHub Actions workflow**：[`.github/workflows/release.yml`](../.github/workflows/release.yml) ~150 行 — `on: push: tags: ['v*']` 触发；3 OS matrix（ubuntu-latest / windows-latest / macos-latest）；每 OS pre-build gate 跑 `tests/test_all.py` + `verify_docs_claims --fast`；`pip install pyinstaller` + `python build.py`；`actions/upload-artifact@v4` per-OS artifact；`release` job 用 `actions/download-artifact@v4` flatten + `sha256sum` 生成 SHA256SUMS.txt + 从 CHANGELOG.md sed 抽取最近一轮 highlights 作 release-notes.md + `softprops/action-gh-release@v2` 创建 **draft** Release（maintainer review 后 publish）；prerelease 自动判定（tag 含 `-`）；零依赖契约保持（PyInstaller 是 build-time，不算 runtime — [ADR 0001](../docs/adr/0001-zero-third-party-dependencies.md) 仍 hold）。RELEASE.md 同步更新反映自动化已实现。
- **B2 — 翻译质量持续验证 retire to architectural decision**：r52 The Tyrant 99.991% 是真实 production 数据 vs lab benchmark；用户每次跑实际项目人工 review 比 nightly mock LLM regression 更有效；mock LLM 不能反映真实 LLM 漂移。CLAUDE.md "已知限制"段记录决策 + 重新评估条件（如未来用户报告 r57 后翻译质量下降，再考虑加固定 fixture 的 quality gate）。
- **B3 — 错误信息中英一致化扫**：扫描结果 — production 代码含 275 处 logger 调用 / 46 distinct prefix（全英文 caps：`[ERROR]` `[WARN]` `[OK]` `[CONFIG]` `[XUAT]` `[TL-MODE]` 等）。审计原 finding 是"中英混用"，实际扫后发现 prefix 已一致（英文 caps 已成熟惯例 + grep 友好 + 跨平台终端兼容），仅 5 处 message body 含英文。Fix：(1) `core/runtime_hook_emitter.py:564` `"skip emit — translation_db empty"` → `"跳过运行时注入：translation_db 为空"`；(2) `core/runtime_hook_emitter.py:616` `"emit failed, continuing: %s"` → `"运行时注入生成失败，已跳过继续后续步骤: %s"`；(3-5) `translators/screen.py` 3 处 self-test counter `"[OK] X: N assertions"` → `"[OK] X 自测通过：N 断言"`。Prefix 全英文 caps 保持不动（已经 inline 文档化为成熟惯例）。
- **B4 — README "免责声明 / Disclaimer" 段**：中英双段都加。中文段：项目 MIT 但翻译产物的法律地位（版权、合理使用、二次创作衍生作品边界）由使用者自行判断和承担；项目维护者不承担法律责任；翻译商业游戏前请确认授权或合理使用边界；解密游戏归档不在范围（[ADR 0004](../docs/adr/0004-renpy-stays-on-dedicated-pipelines.md)）；LLM API 费用由使用者承担；"瑞士军刀"比喻。英文段对应翻译。
- **O1 — `docs/ARCHITECTURE.md §0 Quick Tour for Human Maintainers`**：新加 ~75 行 0 节（在原 §1 模块调用关系之前）。8 子节给**人类 maintainer**而不是 AI 用：(1) 这是个什么项目（一句话定位 + zh-only + 零依赖 + py3.10）；(2) 5 分钟跑通（git clone + test_all + dry-run + onboarding link）；(3) 心理模型（6 包功能简介，emphasize Ren'Py 是 ADR 0004 explicit 例外）；(4) 必读上下文按重要度排序（HANDOFF 250 行 / CLAUDE 150 行 / 5 ADR / 本文 / REFERENCE）；(5) 8 个特殊约束（NEVER push / byte-identical CLAUDE↔.cursorrules / VERIFIED-CLAIMS / 800-line cap / 零欠账闭合 / mypy enforce / ruff 门禁）；(6) 改动前 checklist (3 条最重要：plan-first / 零依赖 / 测试先行)；(7) 加新引擎 7 步指南（参考 r55 Unity XUnity）；(8) 找答案的索引（EVOLUTION 按轮次叙事 / adr/ 主题切片 / git blame / AUDIT_R57.md）。
- **O2 — ROADMAP.md actionable backlog 验证**：r58 P2 创建时已抽取 internal HANDOFF backlog → 公开 ROADMAP.md（按用户视角分类：当前能力 / 短期 ROI 排序 / 中期方向 / 长期愿景 / 已 retire 完整列表）。r59 验证一致性：当前 actionable backlog（Godot + Kirikiri/TyranoBuilder）已 sync 到 ROADMAP § "短期路线图"。
- **O3 — `docs/ONBOARDING.md` 新建 ~150 行**：6 子节（给**新加入的人类贡献者**用）— (0) 项目是什么（一句话定位 + 主要用户场景）；(1) 5 分钟跑通（含失败 fallback reminder）；(2) 我想做什么 → 看哪里（13 行索引表，从 HANDOFF / CLAUDE / ADR / ARCHITECTURE / REFERENCE / EVOLUTION / ROADMAP / CONTRIBUTING / SECURITY / RELEASE / Issue Templates / PR Template）；(3) 我想改代码 → 检查清单（9 项 + 最少跑 2 命令 + 装 ruff/mypy 后 4 命令）；(4) 心理模型（包结构 ASCII art）；(5) Troubleshooting（4 个常见问题：ImportError / docs claims drift / pre-commit hook block / 不要 bypass hook）；(6) 还有什么（maintainer / 主要语言 / hard contracts 数 / 0 CRITICAL streak）。
- **O4 — Community 建设 retire to architectural decision**：项目用户量小（小众游戏汉化工具），Discussions / Discord / sponsor 入口 / contributor list ROI 低于维护成本。CLAUDE.md "已知限制"段记录 + 重新评估条件（如未来"用户量持续增长 + 多人协作开发需求"再考虑开 Discussions + 设立 sponsor 入口）。
- **数字增量**：tests_total 494 unchanged（B3 仅修改字符串内容，0 新测试）; test_files 35 unchanged; ci_steps 36 unchanged（B1 release.yml 是 separate workflow file，不计入 test.yml::jobs.test.steps）; assertion_points 620 unchanged。**纯文档 + 流程 + 微调轮**。
- **hard contracts 仍 15**（无新约束加入；r58 已加 #14 ruff 门禁 + #15 EVOLUTION 滚动归档）。
- **AUDIT_R57.md 收尾**：23 findings 全闭合后，`AUDIT_R57.md` 文件保留作历史 reference（未来轮次可参考审计 framework）。下次类似 audit 应该写 `AUDIT_R<NN>.md` 新文件。

**连续 19 轮 0 CRITICAL correctness 保持**（r35-r59）。

---

## 阶段十九（r60）— EVOLUTION 滚动归档首次执行 + 6 维度新审计 + 20th 0-CRITICAL Streak

2 phases，r60 触发**两个并发动作**：(1) r58 P3 hard contract #15 强制 EVOLUTION 滚动归档首次执行；(2) 用户要求重新做 6 维度审计 + 重写 AUDIT_R57.md 为 r60 audit。

- **本轮触发**：(a) hard contract #15 — r60 是约定的首次"每 5 轮"归档触发点；(b) 用户在 r59 末询问"还有没有其他的技术债 / 质量与安全债 / 架构与设计债 / 流程与文档债 / 产品与业务债 / 组织与知识债，重写 AUDIT_R57.md"——明确要求新一轮深度审计。
- **EVOLUTION 滚动归档（contract #15 首次执行）**：抽阶段十五（r56）/ 阶段十六（r57）/ 阶段十七（r58）/ 阶段十八（r59）/ 阶段十九（r60）5 段完整叙事 → `_archive/EVOLUTION_r56_r60.md`（本文件）；主 EVOLUTION.md 把这 5 段替换为 5 行精简摘要 + 跳转链接；不归档"累积技术资产"段 + "设计原则演进"段（按 P3 contract 留主文件）；wc -l 验证主 EVOLUTION 减 ≥ 100 行（实测约减 -100~-130 行）；下次归档触发 r65 → `_archive/EVOLUTION_r61_r65.md`。
- **r60 6 维度新审计**：扫描确认前几轮已闭合 23 findings 不重复；scan 维度 1-6 找新债务，**收集 23 unique new findings**（**1 HIGH** + **11 MEDIUM** + **11 LOW**）；与 r57 audit 对照证实 22 项是新发现（仅 O4 与 r57 O1 部分重叠，标 retire-confirmed）；fix path 选项 X / Y / Z / W 4 条供用户决策；**本轮仅完成 audit 报告 + 归档**，不实施 fix（用户决策路径后再 r61+ 执行）。
- **新审计 23 findings**（详见根目录 [`AUDIT_R57.md`](../AUDIT_R57.md) 重写版）：
  - **维度 1 技术债 (4)**：T1 (M) `_tl_parser_selftest.py` tempfile 泄漏 / T2 (L) hint 覆盖 44%→43.2% 反向 / T3 (M) `gui.py` 594 接近 800 cap / T4 (L) 缺 benchmark 报告
  - **维度 2 质量与安全债 (4)**：S1 (M) CI matrix 缺 macos-latest（test.yml） / S2 (M) subprocess plugin 协议无 schema version / S3 (L) API key 内存生命周期 / S4 (L) prompt injection 表面（用户 game text→LLM）
  - **维度 3 架构与设计债 (3)**：**A1 (HIGH)** ADR 严重缺漏（r57 T1+T2+S2 + r58 P1+P3+A1 共 6 个架构决策没 ADR 化） / A2 (M) GUI vs CLI subprocess.Popen 间接调用 / A3 (L) `gui.py` 接近 cap（同 T3）
  - **维度 4 流程与文档债 (4)**：P1 (M) HANDOFF 单调增长 / P2 (M) 缺 contributors / acknowledgements / P3 (L) CHANGELOG 自动化 / P4 (L) 测试 fixture 单一化
  - **维度 5 产品与业务债 (4)**：B1 (M) 中断恢复 / SIGTERM / KeyboardInterrupt 路径未审 / B2 (M) 版本号停滞 v1.0.0 vs r59 实际成熟度 / B3 (L) GUI 翻译进度可视化未审 / B4 (L) 多账号 / 多 provider 并发支持
  - **维度 6 组织与知识债 (4)**：O1 (M) 缺 CODE_OF_CONDUCT.md / O2 (M) governance 流程没文档化 / O3 (L) TODO 跟踪机制只在 internal docs / O4 (L) bus factor 仍 = 1（confirm-retire from r57 O1 + r59 O1）
- **本轮特殊**：**纯归档 + 审计轮**，0 代码改动，0 新测试；VERIFIED-CLAIMS 数字 unchanged（tests 494 / files 35 / ci_steps 36 / assertion_points 620）；hard contracts 仍 15；19→20 轮 0 CRITICAL streak（r60 是文档轮，不引入 correctness 风险）。
- **fix 推迟**：r60 audit 报告写好但**未实施**，用户决策 fix path（X / Y / Z / W）后由 r61+ 执行。

**连续 20 轮 0 CRITICAL correctness 保持**（r35-r60）。
