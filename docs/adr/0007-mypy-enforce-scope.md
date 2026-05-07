# 0007. Mypy enforce — 6 文件核心 scope（CI gate）

* 状态：Accepted
* 引入轮次：r57 T2（informational → enforce）/ r58 P1 scope 扩到 engines/+safety/
* 决策者：@Dean20030514
* 关联：[`.github/workflows/test.yml`](../../.github/workflows/test.yml) / [`pyproject.toml::[tool.mypy]`](../../pyproject.toml) / [hard contract #11](../../CLAUDE.md)

## 背景

r36-r56 期间 CI 一直跑 mypy 但用 `|| true` + `continue-on-error: true` 遮蔽错误（informational gate）。结果：mypy 错误持续累积无人 fix。

r57 T2 audit 评估扩 mypy 到 enforce 模式。问题：项目大部分模块没系统加 type hints，全部 enforce 立即失败 hundreds of errors。

## 考虑的方案

1. **全 codebase enforce**：理想但 ROI 低（type hints 覆盖率 ~44%，cleanup cost 巨大）
2. **6 文件核心 scope enforce**：聚焦 LLM API 边界 + 数据持久层（最敏感的 type 错误产生 silent 数据损坏）
3. **保持 informational**：状态 quo，债持续累积

## 决策

选择**方案 2**：6 文件核心 scope enforce。

**Scope**:
- `core/translation_utils.py`
- `core/config.py`
- `file_processor/checker.py`
- `core/api_client.py`
- `core/glossary.py`
- `core/translation_db.py`

实施（r57 T2）：
- CI step 移除 `|| true` + `continue-on-error: true` → `mypy --strict <6 files>`
- 实测 32 errors 全 fix：21 `# type: ignore[union-attr]` 标记 `core/api_plugin.py` 内 runtime-safe Optional Popen 访问；11 真修
- `pyproject.toml::[tool.mypy]` 加配置：`strict = true` / scope 6 files

实施（r58 P1，scope 扩）：
- mypy scope 扩大到 `engines/+safety/`（用 `--follow-imports=silent` 不让 `translators/` 拖累）
- `translators/` 仍有 ~20 mypy errors，留 follow-up 不 gate（明示 informational）

## 后果

正面：
- **核心 LLM 边界 type-safe**：API 客户端 / 数据库 / glossary 三大数据流入口 0 mypy errors
- 新文件加入 scope 前必须先 mypy clean — 鼓励 high-quality type annotation
- `# type: ignore[union-attr]` 仅允许标记 `core/api_plugin.py` 内 runtime-safe 的 Optional Popen 访问点（明示限制）

负面：
- 新 helper 加进 scope 文件需先补全 hint 才能 commit（rate-limit dev 速度）
- mypy 误报需用 ignore comments，少量噪声

中立：
- scope 之外文件（translators/ / pipeline/ / tools/ / gui*.py）仍可有 type errors，不阻塞 CI

## hard contract（#11）

`core/translation_utils.py / core/config.py / file_processor/ / core/api_client.py / core/glossary.py / core/translation_db.py` 6 文件 scope 必须保持 mypy 0 errors；新文件加入 scope 前必须先 mypy clean；`# type: ignore[union-attr]` 仅允许标记 `core/api_plugin.py` 内 runtime-safe 的 Optional Popen 访问点。

## 关联

* 关联 [hard contract #11](../../CLAUDE.md) — Mypy enforce 6 文件 scope
* 关联 [ADR 0009](0009-ruff-ci-gate.md) — 一同构成 r58 lint/format/type 三件套 CI gate
* 关联 r57 audit T2 + r58 audit P1 — 详见 [`_archive/EVOLUTION_r56_r60.md`](../../_archive/EVOLUTION_r56_r60.md) 阶段十六/十七
* 扩 scope 条件：新文件加入需先跑 `mypy --strict <file>` 0 errors；scope 缩窄属于 BREAKING 流程契约变更，必须先 plan-first
