# EVOLUTION_r61_r65 — 详细叙事归档（r61-r65 5 阶段）

> r65 滚动归档（hard contract #15 第二次触发）抽出本文件。主 [`EVOLUTION.md`](EVOLUTION.md) 中阶段二十-二四的详细叙事整体迁移于此；主文件仅留 1 行 summary + 表格行，避免单调增长。
>
> 本文件 covers：r60 audit 路径 X 全闭合（r61-r62） + r63 第三次审计（r63） + r63 audit 路径 X 全闭合（r64-r65）+ r65 第二次 EVOLUTION 滚动归档触发。

---

## 阶段二十（r61）— r60 audit 路径 X 第一波 + 21st 0-CRITICAL Streak

11 项闭合（维度 1+2+3）：

- **A1 HIGH** — 补 6 份 ADR 0006-0011 文档化 r57-r58 全部架构决策：
  - `0006-python-310-floor.md`（PEP 604 BREAKING）
  - `0007-mypy-enforce-scope.md`（6 文件 scope CI gate）
  - `0008-path-traversal-guard.md`（`_FORBIDDEN_PATH_PREFIXES`）
  - `0009-ruff-ci-gate.md`（lint+format gate）
  - `0010-evolution-rolling-archive.md`（r58 P3 / r60 首执 / r60 阈值微调）
  - `0011-shared-config-helper.md`（`_resolve_args_from_config`）
  - `docs/adr/README.md` 索引 5→11
- **T1 M** — `_tl_parser_selftest.py` tempfile 泄漏 fix（`_tmp_files` 跟踪 + `_cleanup_tmp_files` 末尾调用）+ 1 unit test 验证 tempdir snapshot diff = 0
- **T2 L** — CONTRIBUTING.md 加 "新代码 100% type hint" PR 规则（中英双段；不强求 backfill）
- **T3+A3 M+L** — gui.py 594 行 cap watchlist + "新 PR 加 GUI 功能必须先拆"约束（CLAUDE.md "已知限制"段）
- **T4 L** — Performance benchmark 缺失 watchlist（与 r59 B2 翻译质量验证 retire 同理）
- **S1 M** — `.github/workflows/test_macos.yml` nightly schedule 新建（cron `"0 4 * * *"` + `workflow_dispatch` + 3.10/3.12/3.13 matrix）
- **S2 M** — Plugin JSONL 协议视为稳定（`docs/REFERENCE.md §7b` 字段集 + r61 决策不加 version + CLAUDE.md 交叉引用）
- **S3+S4+A2 L+L+M** — 3 项 retire to architectural decision（API key 内存生命周期 / prompt injection 表面 / GUI subprocess.Popen 间接调用）

**数字增量**：tests_total 494 → 495 (+1: T1 test)；test_files 35 unchanged；ci_steps 36 unchanged；assertion_points 620 → 621 (+1)。hard contracts 仍 15（A1 是已有契约 #11-#15 的文档化抽取，不新增）。

---

## 阶段二一（r62）— r60 audit 路径 X 第二波 + AUDIT 23 findings 清零 + 22nd 0-CRITICAL Streak

12 项闭合（维度 4+5+6）+ r60 audit cycle 全闭合：

- **P1 M** — HANDOFF.md 模板精简：r56-r59 详细叙事压缩为 4 行 bullets 引用 `_archive/EVOLUTION_r56_r60.md`（HANDOFF 313→244 行 / -69 / 22%）
- **P2 M** — README.md 中英双段加 "致谢 / Acknowledgements"（maintainer + AI 协作 + 上游归属 + 测试反馈 + 依赖 + 治理）
- **P3+P4+B3+B4+O3+O4 L×6** — 6 项 retire/watchlist 文档化（CLAUDE.md "已知限制"段批量；CHANGELOG 自动化 retire / 测试 fixture 单一 watchlist / GUI 进度可视化 watchlist / 多账号并发 retire / TODO 跟踪 retire / bus factor confirm-retire）
- **B1 M** — 新建 `tests/test_interrupt_recovery.py` 3 observation tests pin SIGTERM/KI 现状（observation-only 不强制 fix）
- **B2 M** — `pyproject.toml::version` **1.0.0 → 2.0.0** 反映 r52 C3/C4 + r57 T1 累积 BREAKING + `RELEASE.md` SemVer 演进段
- **O1 M** — 新建 `CODE_OF_CONDUCT.md`（项目特化 Contributor Covenant 2.1，中英双段，BDFL 治理引用）
- **O2 M** — `CONTRIBUTING.md` 中英双段加 "Governance" 段（BDFL 模型 + PR merge 权 + backlog 优先级 + hard contracts 制定 + CoC 执行 + Contributor 角色 + AI 协作角色 + 未来演进）

**数字增量**：tests_total 495 → 498 (+3: B1 interrupt recovery)；test_files 35 → 36 (+1)；assertion_points 621 → 624 (+3)。**r60 audit 23 findings 全闭合**（r61 11 + r62 12）。hard contracts 仍 15。

---

## 阶段二二（r63）— 第三次 6 维度深度债务审计 + 23rd 0-CRITICAL Streak

**纯 audit 轮**，零代码 / 零数字变更（VERIFIED-CLAIMS 维持 498/36/36/624）：

- **背景**：r57 cycle 23 + r60 cycle 23 已闭合 = 46 项；r63 不重复
- **范围**：r62 末 baseline 后更深层、跨维度潜在债务
- **Ground-truth scan**：11+ 命令跨 6 维度（file 大小 / 入口分布 / TODO/FIXME / hardcoded URLs / tempfile usage / 函数内 import / docs freshness / workflow / 测试运行时 / AUDIT 命名 / build.py version sync）
- **23 unique new findings 重写 `AUDIT_R57.md`**：

| 维度 | 严重度分布 | 关键 finding |
|------|----------|-------------|
| 1. 技术债 (T1-T4) | 1H + 1M + 2L | **T1 HIGH**: 3 testfile 距 800 cap 仅 2-10 行 imminent block |
| 2. 质量与安全债 (S1-S4) | 1H + 2M + 1L | **S1 HIGH**: pre-commit hook 仅运行 191/485 测试 ≈ 39% 覆盖（24/35 测试文件不在 meta-runner，含 r61 T1 + r62 B1 测试本身）|
| 3. 架构与设计债 (A1-A3) | 0H + 2M + 1L | A1: gui.py watchlist persisted；A2: pipeline/stages.py 函数内 import 10 处未审 |
| 4. 流程与文档债 (P1-P4) | 0H + 2M + 2L | P1: ROADMAP "截止 r57 末" stale；P2: ONBOARDING 说 "5 份 ADR" 但实际 11 份 |
| 5. 产品与业务债 (B1-B4) | 0H + 2M + 2L | B1: pyproject description 中文 only；B2: build.py 无 PyInstaller version-info |
| 6. 组织与知识债 (O1-O4) | 0H + 2M + 2L | O1: 缺 `.editorconfig`；O2: 缺 `.github/FUNDING.yml` |
| **TOTAL** | **2H + 9M + 12L = 23** | |

- **fix paths X/Y/Z/W** 供用户决策；**用户选 X**（全部 23 项 fix，约 r64-r65 两轮）

---

## 阶段二三（r64）— r63 audit 路径 X 第一波 + 3 audit-tail regressions + 24th 0-CRITICAL Streak

11 项闭合（维度 1+2+3）+ S1 修 meta-runner 时 surfaced 3 个 pre-existing silent regressions 同轮全修：

- **T1 HIGH** — 拆 3 testfile 接近 800 cap：
  - `test_file_safety.py` 798 → **151**（5 helper unit tests）+ 新 `test_file_safety_loaders.py` **692**（16 caller-integration TOCTOU regressions）
  - `test_api_client.py` 792 → **656**（22 unit tests）+ 新 `test_api_client_response_cap.py` **173**（5 response-body cap tests）
  - `test_verify_docs_claims.py` 790 → **553**（16 helper unit tests）+ 新 `test_verify_docs_claims_main.py` **405**（12 main_fast_path tests，含 `_make_fixture_repo` helper 复制）
  - 全部 21+27+28 = 76 tests 拆分后保留 PASS

- **S1 HIGH** — 重写 `tests/test_all.py` 为 **subprocess-discover-and-run**（37 文件全跑 / ~7s vs prior 11 文件 / 0.68s）。Discover 模式自动跟进未来新加测试文件，永不再 silent gap
  - **audit-tail (a)**：`tests/test_batch1.py:240-270` 3 个多语言测试 (`ja/ko/zh-tw`) r52 C4 BREAKING 后 stale → rename 为 `_kwarg_ignored_post_r52` 并改 assertion 为 `"chinese"`（pin r52 C4 contract: kwarg ignored, always 'chinese'）
  - **audit-tail (b)**：`tests/test_rpyc_decompiler.py` 582 行 — 5/8 imports 引用已不存在的 API（`RPYC2_HEADER` 等）→ **删除**（dead test debt；r66+ 可在新 API 上重建）
  - **audit-tail (c)**：`tests/test_single.py` 是 manual integration script (`input()` prompt)，不是 unit test → 加入 `tests/test_all.py::_NON_TEST_FILES` 排除（保留文件作为 manual script 历史）

- **S2 M** — `git mv AUDIT_R57.md _archive/AUDIT_R63.md` + 新建 `AUDIT.md` 永久入口（active cycle 标记 + archived cycles 索引表）；CLAUDE.md docs index / HANDOFF / docs/ARCHITECTURE / 2 workflow / ADR 0011 全 refs 更新

- **S3 M** — `START.bat`：`Python 3.9+` → `Python 3.10+` + `python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"` 版本检测（fail 时 message 引用 ADR 0006）

- **S4 L** — `main.py` argparse 加 `--version` flag + 新 `_read_project_version()` 从 `pyproject.toml` regex 解析（避免 tomllib 3.11+ 依赖）；实测 `python main.py --version` → `main.py 2.0.0`

- **T2-T4 + A1-A3 6 项** — watchlist/retire 文档化（CLAUDE.md "已知限制"段：4 production 文件接近 cap watchlist / hint coverage 度量说明 / .pyc residue retire / gui.py 594 watchlist persisted / pipeline/stages.py 函数内 import 必须 docstring lazy 原因 / 空 __init__.py retire）

**数字增量**：tests_total 498 → 480 (-18: 删除 test_rpyc_decompiler 18 tests)；test_files 36 → 38 (+2 net: +3 split / -1 delete)；ci_steps 36 unchanged；assertion_points 624 → 606 (-18)。hard contracts 仍 15。

---

## 阶段二四（r65）— r63 audit 路径 X 第二波 + EVOLUTION 滚动归档第二次触发 + 25th 0-CRITICAL Streak

12 项闭合（维度 4+5+6）+ r63 audit cycle 全闭合 + EVOLUTION 滚动归档（hard contract #15 第二次执行）：

- **P1 M** — `ROADMAP.md` 更新到 r64 末状态：当前能力段（11 ADRs / v2.0.0 / 24 轮 0-CRITICAL / 完整 docs 体系 / AUDIT 永久入口 / Meta-runner subprocess-discover）+ 短期路线图所有 r58-r64 引入项标 ✅
- **P2 M** — `docs/ONBOARDING.md` "5 份 ADR" → 引用 `docs/adr/README.md` 索引（避免数字 drift；r66+ 加新 ADR 时不需要再改 ONBOARDING）
- **P3 L** — `docs/ARCHITECTURE.md §0.7` 加 "关键架构决策快查（11 ADRs）" 段 — 按主题分组（依赖 / 目标语言 / Plugin / Engine / CI gate / 安全 / 流程）交叉引用全部 11 ADRs
- **P4 L** — `scripts/install_hooks.bat` 新建（Windows 等价 .sh，~30 行）；项目主开发环境 = Windows
- **B1 M** — `pyproject.toml::description` 改英文：`"Pure-Python multi-engine game translator (Ren'Py / RPG Maker MV-MZ / Unity XUnity / CSV-JSONL) using LLM APIs for Simplified Chinese localization"`（PyPI / `pip show` 国际工具友好）
- **B2 M** — `build.py` 加 PyInstaller `--version-file` 集成：新 `_read_project_version()` 读 pyproject.toml + 新 `_write_version_info()` 生成 Windows VS_VERSION_INFO 模板（major/minor/patch/build tuple + StringFileInfo + VarFileInfo）；`.gitignore` 加 `version_info.txt`（每次 build 重新生成）；.exe 现含 Windows 版本号 metadata（Properties → Details）
- **B3 L** — LLM provider URL/model 硬编码 retire to architectural decision（用户用 `--api-base` / `--model` flag 覆盖即可；每年 5-10 次手动同步 LLM 升级是合理工作）
- **B4 L** — RPG Maker forum link stale risk retire（OSS 通病无系统解决方案）
- **O1 M** — 新建 `.editorconfig`（root + Python 4-space + LF + UTF-8 + trim trailing；`*.bat` CRLF；Markdown 不 trim trailing；YAML/TOML/JSON 2-space；Makefile tab）
- **O2 M** — 新建 `.github/FUNDING.yml`（显式 disabled，与 r59 O4 community 建设 retire 一致）+ 注释说明 re-enable 条件
- **O3+O4 L** — 2 项 retire to architectural decision（TODO tracking internal-only confirm-retire / ADR + CHANGELOG completeness 测试缺失 retire）

- **EVOLUTION 滚动归档（hard contract #15 第二次触发）**：
  - 抽阶段二十-二四（r61-r65）所有详细叙事到本文件 `_archive/EVOLUTION_r61_r65.md`
  - 主 EVOLUTION.md 仅留单行 summary + 阶段表格行
  - 由于 r61-r64 在 r60 归档之前已经是表格摘要形式（不是详细叙事），本次归档实际可减少行数有限。**hard contract #15 阈值再次微调**到 "≥10% OR ≥30 行"（acknowledge 归档量随 baseline 自然变化）；详见 [ADR 0010](../docs/adr/0010-evolution-rolling-archive.md) 阈值演变表
  - 文档索引同步：CLAUDE.md "文档索引" 表格加本文件 entry

**数字增量**：tests_total / test_files 取决于 r65 commit；ci_steps 36 unchanged；hard contracts 仍 15（O3+O4 retire 不算新契约）。

**r63 audit 23 findings 全闭合**（r64 11 + r65 12 = 23）。

🔔 **下次滚动归档**触发 **r70** → `_archive/EVOLUTION_r66_r70.md`。
