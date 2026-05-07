# 0009. Ruff lint+format — CI gate

* 状态：Accepted
* 引入轮次：r58 P1
* 决策者：@Dean20030514
* 关联：[`.github/workflows/test.yml`](../../.github/workflows/test.yml) / [`pyproject.toml::[tool.ruff]`](../../pyproject.toml) / [hard contract #14](../../CLAUDE.md)

## 背景

r57 末项目代码风格散乱：
- 部分文件 black 格式化过，部分手工排版
- import 顺序不统一（部分按 stdlib / third-party / local 排序，部分混乱）
- 长行 / 末尾空格 / 空 except 等小毛病散布
- 没自动化 lint，依赖人工 review 抓

PEP 8 是 style guide 不是 enforcer。需要工具自动化。

## 考虑的方案

1. **black + isort + flake8**：传统三件套，三个 tool 配置维护成本高
2. **ruff**：单一 tool 同时 lint + format（black-compatible），Rust 实现速度快 100x
3. **pyright + black**：放弃 lint，仅 type check + format

## 决策

选择**方案 2**：ruff lint + format CI gate。

实施（r58 P1）：
- `pyproject.toml::[tool.ruff]` 配置：
  - `target-version = "py310"`（与 [ADR 0006](0006-python-310-floor.md) 一致）
  - `line-length = 120`（项目惯例）
  - `[tool.ruff.lint] select = ["E", "F", "W"]`（pycodestyle errors + pyflakes + warnings）
  - `[tool.ruff.lint] extend-ignore = ["E402", "E501", "F841"]`：
    - E402（module-level import not at top）— 容忍 lazy import / `import os; sys.path.insert(...)` 边界文件
    - E501（line too long）— line-length 120 已宽松，无意义重复
    - F841（unused variable）— 容忍 `result, _ = func()` unpacking
  - `[tool.ruff.format] quote-style = "double"`（项目惯例）
- CI 加 2 step：`ruff check .` + `ruff format --check .`
- 一次性 baseline：`ruff format .` 99 files reformatted（生成 r58 P1 大 commit）+ `ruff check --fix .` 132 errors auto-fixed

## 后果

正面：
- **代码风格机械化一致**：人工 review 不再耗在格式问题
- **速度快**：ruff Rust 实现，full repo lint < 1 second（black 需 ~10s）
- 单一 tool 配置（vs black+isort+flake8 三套配置文件）
- 与 [ADR 0001](0001-zero-third-party-dependencies.md) 不冲突：ruff 是 dev-time tool，不进 production import；零依赖契约仅约束 runtime
- **导入顺序自动维护**：原 isort 功能 ruff 内置（`I` rule，未启用但可未来加）

负面：
- 新 contributor 必须本地 `pip install ruff`（与 mypy 同样要求）
- E402/E501/F841 ignore 列表有审美争议（部分用户偏好严格）
- ruff format 与 black 99% 兼容但偶有差异（项目用 ruff format 不是 black，避免双重格式化战）

中立：
- 不引入 import sort enforcement（`I` rule 未启用），降低噪声

## hard contract（#14）

任何新 PR 必须 `ruff check .` + `ruff format --check .` 全过；`pyproject.toml [tool.ruff.lint] extend-ignore` 列表（E402 / E501 / F841）不得放宽；新规则只能加不能减。

## 关联

* 关联 [hard contract #14](../../CLAUDE.md) — CI ruff lint/format 门禁
* 关联 [ADR 0001](0001-zero-third-party-dependencies.md) — ruff 是 dev-time tool 不破坏零运行时依赖
* 关联 [ADR 0007](0007-mypy-enforce-scope.md) — 一同构成 r58 lint/format/type 三件套 CI gate
* 关联 r58 audit P1 — 详见 [`_archive/EVOLUTION_r56_r60.md`](../../_archive/EVOLUTION_r56_r60.md) 阶段十七
* 放宽 extend-ignore 列表条件：必须先 plan-first 论证；新规则加入只需 PR review
* 替换 ruff 条件：极小概率，需另一 tool 在 lint+format 都 ≥ ruff 才考虑
