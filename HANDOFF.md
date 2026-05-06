# HANDOFF — Round 51 末 → Round 52 起点

<!-- VERIFIED-CLAIMS-START -->
tests_total: 514
test_files: 36
ci_steps: 39
assertion_points: 640
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

纯 Python 零依赖多引擎游戏汉化工具。**Round 51 末完成 GitHub 仓库重命名 sync**（`Renpy-Translator` → `Multi-Engine-Game-Translator`，pyproject + `$schema` + 17 sites logger namespace + README 历史注解 + 4 contract tests pin），**zero-debt closure 模式第二次执行**（5 Coverage findings 同轮 4 fix + 1 architectural decision），**连续 11 轮 0 CRITICAL correctness**（r35-r51）。

## 同步状态

- r51 共 **7 commits**（5 主线 A1-A6 + C2 Coverage findings + docs sync + audit-tail）已全部 push 至 origin/main
- 当前 `origin/main` = `4d10779`（r51 audit-tail：fix CI grep self-trip）
- 本地 `main` 与 `origin/main` 同步（`git status` → "up to date"）
- pre-commit hook 已激活（`git config core.hooksPath = .git-hooks`）
- 4 件套自动 enforce：py_compile + 800 行 cap + meta-runner + `verify_docs_claims --fast`
- Git remote: `https://github.com/Dean20030514/Multi-Engine-Game-Translator.git`（r51 A1 同步）

## 架构健康度（核心维度）

| 维度 | 状态 |
|------|------|
| 大文件（> 800 行） | ✅ 全 .py < 800（pre-commit + verify_docs_claims --fast 自动 enforce） |
| 数据完整性 | ✅ TranslationDB 线程安全（RLock）+ 原子写入（os.replace）+ schema v2 partial backfill |
| 反序列化安全 | ✅ 3 处 pickle 全白名单（`core/pickle_safe.py` + rpyc Tier 1+2 + rpa_unpacker） |
| 插件沙箱 | ✅ Dual-mode（importlib 快路径 + opt-in subprocess）+ 三通道防护（stdout 50M chars + stderr 10K + stdin lifecycle） |
| 多语言完整栈 | ✅ 5 层 code-level contract（prompt + alias-read + checker + zh-tw 隔离 + generic fallback） |
| OOM 防护 | ✅ 23/23 user-facing path-stat + 26 sites / 12 modules TOCTOU MITIGATED via `core.file_safety` 共享 helper |
| Mock target stale trap | ✅ CI grep step 兜底（防 r48 trap CLASS 复发；r50 C4 filter 放宽到 `file_safety` 兼容 qualified form；r51 audit-tail 加第三级 `test_repo_rename_consistency` filter 豁免 documentation-only 文件 self-trip） |
| Repo rename consistency | ✅ Round 51 加 4 contract tests 钉自身 repo URL refs + logger namespace + 上游归属反向 exhaustiveness |
| 模块分层 | ✅ deferred import 保 layering（`file_processor` 不在 module load 时 import `core`） |
| docs claim drift | ✅ 4 项 prevention 自动化（pre-commit hook + `verify_docs_claims --fast`/`--full` + `VERIFIED-CLAIMS` 单一声称源） |
| debt closure | ✅ Round 50 起规则强制：所有 findings 同轮 fix，零 deferred；r51 第二次执行无 backlog |
| 累计审计 | ✅ 连续 11 轮 0 CRITICAL correctness（r35-r51） |

## 推荐的 Round 52+ 工作项

> Round 51 完成时**零 deferred actionable items**。下列均为 r52+ 候选新工作。

### 🟢 短平快（无外部资源）

1. **Round 52 起始审计** — 回溯验证 r51 4 Coverage fixes + 1 architectural decision 在 production code path 上 robust（特别注意 logger rename 是否在 r52 任何 GUI / pipeline 改动后仍 100% sites synced）
2. **CHANGELOG 5 轮滚动维护**（**defer trigger**：r52 第一次主线 audit/feature commit 落盘后，与 docs sync 同 commit 执行；不要单独提前做，否则会截短真实历史） — 删 r47 detail / 加 r52 detail / rename `_archive/CHANGELOG_RECENT_r51.md` → `_r52.md` / sync `EVOLUTION.md` r52 概要 + `CHANGELOG.md` "最近 5 轮" 表（r51 已建立 r51.md 命名体例 + 5 轮窗口）
3. **r51 audit-tail 检查**（如果 push 后用户反馈触发）— 同 r48 audit-2/3/4 chain 模式

### 🟠 需真实 API + 游戏（独立一轮）

4. **非中文目标语言端到端验证**（生产 ja / ko / zh-tw） — r39-r48 多层契约已锁死
5. **A-H-3 Medium**：adapter 让 Ren'Py 走 generic_pipeline 6 阶段
6. **A-H-3 Deep**：完全退役 DialogueEntry
7. **S-H-4 Breaking**：强制所有 plugins 走 subprocess
8. **RPG Maker Plugin Commands (code 356)**
9. **加密 RPA / RGSS 归档**

### ⚫ 监控项（informational watchlist，not actionable debt）

- Pickle 白名单 `_codecs.encode` / `copyreg._reconstructor` 理论链式攻击
- HTTP 响应体 64 KB 精度偏差
- TOCTOU fstat 自身 race 窗口（极小 microsecond 级）
- Symlink path-swap TOCTOU（current codebase 无 exploit vector，本地 single-user 工具 not actionable）
- Logger namespace 行为契约（r51 architectural decision）— 静态 orphan grep 充分；如未来引入 logging filter / sink / metric pipeline，需 reconsider

---

## 关键文件路径速查

| 类别 | 路径 |
|------|------|
| AI 全局上下文 | `CLAUDE.md` / `.cursorrules`（byte-identical） |
| 本次交接 | `HANDOFF.md`（本文件） |
| 用户面文档 | `README.md`（中英双语） |
| 变更日志 | `CHANGELOG.md`（极简入口）+ `_archive/EVOLUTION.md`（r1-r51） |
| 全量历史 | `_archive/CHANGELOG_FULL.md` + `_archive/CHANGELOG_RECENT_r51.md`（r47-r51 详细） |
| 入口 | `main.py` / `gui.py`（mixin） / `one_click_pipeline.py` |
| 引擎抽象 | `engines/{engine_base, engine_detector, generic_pipeline, renpy_engine, rpgmaker_engine, csv_engine}.py` |
| 核心 | `core/{api_client, api_plugin, config, glossary, prompts, translation_db, translation_utils, lang_config, http_pool, pickle_safe, font_patch, runtime_hook_emitter, file_safety}.py` |
| 流水线 | `pipeline/{helpers, gate, stages}.py` |
| 测试 | `tests/test_all.py` meta-runner + 34 独立 suites（含 r51 新加 `test_repo_rename_consistency.py`） |
| docs | `docs/ARCHITECTURE.md`（架构 + 数据流 + 校验链 + 引擎指南 + 测试体系）+ `docs/REFERENCE.md`（常量 + 错误码 + 路线图） |
| CI | `.github/workflows/test.yml`（双 OS matrix × 3 Python = 6 jobs，38 steps）+ `scripts/verify_workflow.py` |
| 开发者工具 | `.gitattributes` + `.gitignore` + `build.py --clean-only` + `.git-hooks/pre-commit` + `scripts/{install_hooks.sh, verify_workflow.py, verify_docs_claims.py}` |

---

## 下次新对话接手指南

**必读顺序**（上下文从零开始）：

1. **本文件** — 当前状态 + 推荐工作项 + 文件路径
2. **`CLAUDE.md`** — 项目身份 + 10 大开发原则 + 模块图
3. **`docs/ARCHITECTURE.md`** + **`docs/REFERENCE.md`** — 架构与常量
4. **（按需）** `_archive/EVOLUTION.md` — 历史决策（含 r51 段）
5. **（按需）** `_archive/CHANGELOG_RECENT_r51.md` — 最近 5 轮（r47-r51）详细

**Round 52 关键约束**：
- audit findings 必须**同轮 fix，no tier exemption**（r50 起 written + enforced；r51 第二次执行验证有效）
- 数字声称只在本文件 `VERIFIED-CLAIMS` 块声明
- 修改 `CLAUDE.md` 必须同步 `.cursorrules`
- 修改 logger namespace / repo URL self-references 必须保持 `tests/test_repo_rename_consistency.py` 4 contract tests 全 PASS（r51 加固）
- 6 处 anonymousException 上游归属永远不能被任何 sed/refactor 误删
- pre-commit hook 已激活，会自动 enforce file-size cap + drift check
