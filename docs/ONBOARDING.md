# Onboarding — 5 分钟跑通 + 找答案的索引

> r59 O3 引入。本文目标：让新加入的人类贡献者**5 分钟内**知道项目能跑、知道下一步看什么。
>
> 想看完整架构 / 历史决策 / 路线图请去 [`ARCHITECTURE.md`](ARCHITECTURE.md) / [`../_archive/EVOLUTION.md`](../_archive/EVOLUTION.md) / [`../ROADMAP.md`](../ROADMAP.md)。本文是**入口**不是 reference。

---

## 0. 项目是什么

游戏汉化工具：把 Ren'Py / RPG Maker / Unity XUnity / CSV-JSONL 的可翻译文本喂给 LLM，自动回填到原文件。**目标语言固定 zh 简体中文**。**零运行时依赖**，纯 Python ≥ 3.10。

主要用户场景：玩家想给小众游戏出汉化补丁，但不想 / 没能力手翻 50000+ 句对话。

---

## 1. 5 分钟跑通

```bash
# 克隆
git clone https://github.com/Dean20030514/Multi-Engine-Game-Translator
cd Multi-Engine-Game-Translator

# 跑测试看是否绿
python tests/test_all.py
# 期望: ALL N TESTS PASSED（N 见 HANDOFF.md VERIFIED-CLAIMS 块）

# dry-run（不调 API，仅扫描估费）
python main.py --game-dir tests/tl_priority_mini/game --provider xai --dry-run

# 帮助
python main.py --help
```

如果 `tests/test_all.py` 没绿，先**不要**改代码——这一定是环境问题（Python 版本错？workspace 不全？）。看 [Troubleshooting](#troubleshooting) 段。

---

## 2. 我想做什么 → 看哪里

| 我想… | 看这里 |
|------|------|
| 知道项目当前状态 | [`HANDOFF.md`](../HANDOFF.md) — 当前轮次 + 已完成 + 推荐下一步 + Round N+1 约束 |
| 理解 10 大开发原则 + 模块图 + 维护规则 | [`CLAUDE.md`](../CLAUDE.md) |
| 找架构决策 / "为什么这样设计？" | [`CLAUDE.md`](../CLAUDE.md) "维护规则"段 hard contracts 列表 + [`_archive/EVOLUTION.md`](../_archive/EVOLUTION.md) 阶段叙事（r66 retire ADR framework）|
| 看完整模块图 / 三种翻译模式数据流 / 一键流水线 | [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — 顶部 §0 是给人类的 Quick Tour |
| 调阈值常量 / 看错误码 / 看引擎路线图 | [`docs/REFERENCE.md`](REFERENCE.md) |
| 看历史叙事（按轮次组织） | [`_archive/EVOLUTION.md`](../_archive/EVOLUTION.md) |
| 看公开路线图 / 哪些功能 retire 了 | [`ROADMAP.md`](../ROADMAP.md) |
| 提交贡献的格式 / 流程 | [`CONTRIBUTING.md`](../CONTRIBUTING.md) |
| 报告 bug / 提功能请求 | [`.github/ISSUE_TEMPLATE/`](../.github/ISSUE_TEMPLATE/) — bug_report.md + feature_request.md |
| 提交 PR | [`.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md) |
| 报告安全漏洞 | [`SECURITY.md`](../SECURITY.md) — 走 GitHub Security Advisory，**不要**在 public issue |
| 发布新版本（仅 maintainer） | [`RELEASE.md`](../RELEASE.md) |

---

## 3. 我想改代码 → 检查清单

按 [`CLAUDE.md`](../CLAUDE.md) "修改代码前的检查清单"：

1. ✅ 跑 `python tests/test_all.py` 确认 baseline 绿
2. ✅ 多文件 refactor 必须先 plan-first（提 issue / discussion 先讨论；CLAUDE.md 第 7 原则）
3. ✅ 不引入第三方 runtime 依赖（CLAUDE.md 第 9 条 hard contract）
4. ✅ 文件不能超 800 行（pre-commit hook 会 block）
5. ✅ 改 [`CLAUDE.md`](../CLAUDE.md) 必须 `cp CLAUDE.md .cursorrules`（byte-identical 契约）
6. ✅ 数字声称只在 [`HANDOFF.md`](../HANDOFF.md) `VERIFIED-CLAIMS` 块（pre-commit hook 验证）
7. ✅ 新加 `core/translation_utils.py` / `core/config.py` / `file_processor/` / `core/api_client.py` / `core/glossary.py` / `core/translation_db.py` 6 文件 scope 内代码必须 mypy clean（r57 T2）
8. ✅ `engines/+safety/` 也必须 mypy clean (`--follow-imports=silent`，r58 P1)
9. ✅ `ruff check .` + `ruff format --check .` 必须 green（r58 P1）

跑 PR 前最少这两条命令必须过：

```bash
python tests/test_all.py
python scripts/verify_docs_claims.py --fast
```

如果你装了 ruff + mypy（CI 自动装），也跑：

```bash
ruff check .
ruff format --check .
mypy --ignore-missing-imports core/translation_utils.py core/config.py file_processor/ core/api_client.py core/glossary.py core/translation_db.py
mypy --ignore-missing-imports --follow-imports=silent engines/ safety/
```

---

## 4. 心理模型 — 主要包做什么

```
engines/        多引擎抽象层（Ren'Py 是特殊路径，详见 docs/REFERENCE.md §13.2.1）
translators/    Ren'Py 专用三条管线（tl / direct / retranslate）+ 5 层 fallback + r53 retry 优化
core/           LLM API + 共享基础设施（连接池 / pickle 白名单 / 术语表 / translation_db）
safety/         cross-cutting helper（TOCTOU 防御，r56 M2 从 core/ 移出独立）
file_processor/ .rpy 文本处理（splitter / patcher / checker / validator）
pipeline/       一键四阶段流水线（pilot → gate → full → catchup）
tools/          独立 CLI 工具（RPA 解包 / rpyc 反编译 / lint 修复 / 校对编辑器）
custom_engines/ 用户自定义翻译引擎插件（subprocess sandbox-only，r52 C3 BREAKING；详见 CLAUDE.md "项目身份"段）
scripts/        verify_docs_claims / install_hooks / migrate_db_v2_to_v1
tests/          单元 / 集成 / fuzz / 红队 / 复杂 fixture round-trip 测试
docs/           ARCHITECTURE / REFERENCE / ONBOARDING（本文）
_archive/       历史归档（EVOLUTION 按轮次叙事 / CHANGELOG_RECENT 最近 5 轮 detail）
```

---

## 5. Troubleshooting

### `tests/test_all.py` 报 ImportError

通常是 Python 版本错。项目要求 Python ≥ 3.10（PEP 604 `int | None` 语法）。

```bash
python --version   # 必须 ≥ 3.10
```

如果你装了多个 Python，确认用对的：

```bash
which python   # Linux/macOS
where python   # Windows
```

### `verify_docs_claims --fast` 说数字 drift

数字声称只在 [`HANDOFF.md`](../HANDOFF.md) 顶部 `VERIFIED-CLAIMS` fenced block。其他文档不能再写 `tests_total: N`。如果你的改动让数字变了，更新 HANDOFF 的 fenced block，**不要**改其他 docs 里的数字。

### `pre-commit hook` block 我的 commit

按 hook 输出的提示修。常见：
- 800 行 cap：拆文件
- VERIFIED-CLAIMS drift：更新 HANDOFF
- meta-runner fail：跑 `python tests/test_all.py` 看哪个测试 fail
- byte-identical 不一致：`cp CLAUDE.md .cursorrules`

### 我想跳过 hook

**不要**。hook 是 r35-r58 累积的契约边界，跳过 = 引入 silent debt。如果 hook 误报，**改 hook**而不是 bypass（issue 报 bug）。

---

## 6. 还有什么

- 项目维护者：@Dean20030514
- 主要开发语言：中文（除 in-repo code/comments/commits 仍英文）
- 国际贡献者：README + CONTRIBUTING 双语；其他 docs 仅中文
- 当前 hard contracts：15 项（详见 [`CLAUDE.md`](../CLAUDE.md) "维护规则"段）
- 当前 0 CRITICAL streak：r35 至今（详见 [`HANDOFF.md`](../HANDOFF.md) 状态一句话）

完整入门：本文 + [`CLAUDE.md`](../CLAUDE.md) + [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) §0 = 你需要的全部。其他 docs 都是 reference，按需查。
