# Changelog

最新数字（测试数 / 文件数 / CI 步骤 / 断言点）见 [HANDOFF.md](HANDOFF.md) 顶部 `VERIFIED-CLAIMS` 块。完整历史见 [_archive/](_archive/)。

## 最近 5 轮（仅高亮，详细见归档）

- **Round 53** — **W1-W4 主线全闭合 + 6 监控项重新评估**：(W1) `tl_mode.py` retry 拆到新模块 `translators/_tl_retry.py` (174 行) + ThreadPoolExecutor + per-chunk progress log + 自适应 chunk size；(W2) `core/api_client.py::_extract_json_array` 加 layer-7 char-walker `_repair_unescaped_quotes_in_strings` 修字符串值内未 escape `"`；(W3) layer-6 LLM ID drift detection (`detect_id_drift()` 主 stage + retry stage 各注入；symmetric-difference > 10% warn)；(W4) direct-mode English-only 文档化 (启动 INFO log + 常量 docstring + README + CLAUDE.md)；监控 #1 pickle 白名单 8/8 红队 verified safe；监控 #2 HTTP 64 KB 精度偏差降至 1 B；监控 #3+#5+#6 retire to architectural decision；监控 #4 symlink CLI warning + `--allow-symlink` flag。Plus 36 单元测试新增 (17 W1+W3 / 5 W2 / 3 #2 / 8 #1 / 3 #4)。
- **Round 52** — **scope reduction BREAKING**：(C1) HANDOFF push-status drift checker；(C2) build.py CI smoke + GUI architectural decision；(C3 BREAKING) retire importlib plugin loader（subprocess 沙箱成唯一模式）；**(C4 BREAKING) drop multi-target language support**（删 `core/lang_config.py` + `--target-lang` flag + multi-lang outer loop + 5 层 contract + DB v2 schema + runtime-hook v2 schema + 4 测试文件 + `tools/merge_translations_v2.py`；目标语言固定 zh；存量 v2 DB 用 `scripts/migrate_db_v2_to_v1.py` 迁移）
- **Round 51** — GitHub 仓库重命名 sync `Renpy-Translator` → `Multi-Engine-Game-Translator`；4 contract tests pin repo URL + logger namespace；zero-debt closure 模式第二次执行
- **Round 50** — Zero-debt closure 模式确立（所有 audit findings 同轮 fix，no tier exemption）；r49 6 项 deferred 全 closure；2 latent fixture bug 同轮 fix；CI Mock target consistency check
- **Round 49** — Drift prevention 工具自动化（pre-commit + verify_docs_claims --fast/--full + VERIFIED-CLAIMS 单一声称源）；file_safety helper 推广 26 sites / 12 modules 全 TOCTOU MITIGATED

## 阶段总览

详见 [_archive/EVOLUTION.md](_archive/EVOLUTION.md)。

| 阶段 | 轮次 | 主题 |
|------|------|------|
| 阶段零 | r1-r10 | 翻译质量基线 |
| 阶段一 | r11-r17 | 架构成型（main.py 拆分 + 引擎抽象 + GUI） |
| 阶段二 | r18-r19 | 工具链补全（RPA/rpyc/lint/editor/插件） |
| 阶段三 | r20-r30 | 安全与稳健化（pickle 白名单 + ZIP Slip + 大文件拆分 + 沙箱） |
| 阶段四 | r31-r35 | 多语言与运行时注入（v2 schema + 外层语言循环） |
| 阶段五 | r36-r42 | 防御加固与契约化（OOM cap + checker per-language） |
| 阶段六 | r43-r45 | 累计审计期（CI Windows + plugin char/byte 澄清） |
| 阶段七 | r46-r48 | Auto Mode 综合执行（GUI smoke + TOCTOU helper） |
| 阶段八 | r49 | Drift Prevention 自动化（4 项工具 + 26 sites MITIGATED） |
| 阶段九 | r50 | Zero-Debt Closure 模式确立 |
| 阶段十 | r51 | GitHub 仓库重命名 sync + 4 contract tests pin |
| 阶段十一 | r52 | **Scope reduction BREAKING**（retire importlib plugin + drop multi-target language；只保留 zh 目标） |
| 阶段十二 | r53 | **W1-W4 主线 + 6 监控项重新评估**（retry 并发化 + JSON escape-fix + ID drift detection + direct-mode 文档化；pickle 红队 verified + HTTP 精度收紧 + symlink mitigation + 3 项 retire） |

## 归档索引

- [_archive/EVOLUTION.md](_archive/EVOLUTION.md) — r1-r50 演进概览（无 commit hash，保 round 编号）
- [_archive/CHANGELOG_RECENT_r50.md](_archive/CHANGELOG_RECENT_r50.md) — Round 50 末归档的最近 5 轮详细
- [_archive/CHANGELOG_FULL.md](_archive/CHANGELOG_FULL.md) — r1-r45 总览表 + r19/r43 完整正文
- [_archive/TEST_PLAN_r50.md](_archive/TEST_PLAN_r50.md) — Round 50 末归档的测试覆盖明细
