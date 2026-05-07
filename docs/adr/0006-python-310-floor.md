# 0006. Python ≥ 3.10 (PEP 604 union syntax) — BREAKING

* 状态：Accepted
* 引入轮次：r57 T1
* 决策者：@Dean20030514
* 关联：[`pyproject.toml::requires-python`](../../pyproject.toml) / [`HANDOFF.md`](../../HANDOFF.md) "Round 57 完成" 段 / [hard contract #12](../../CLAUDE.md)

## 背景

r57 T1 audit 扫描全 .py 源码发现 7 个文件用 PEP 604 联合类型语法（`int | None` / `str | bytes`）：

| 文件 | 涉及行 |
|------|------|
| `core/api_client.py` | type hints |
| `core/api_plugin.py` | type hints |
| `engines/engine_base.py` | dataclass field |
| `engines/generic_pipeline.py` | helper signatures |
| `engines/unity_xunity.py` | r55 新加 |
| `pipeline/stages.py` | helper signatures |
| `safety/file_safety.py` | helper signatures |

PEP 604 在 Python 3.10 起作为运行时语法支持；3.9 下使用必须 `from __future__ import annotations`（lazy evaluation 模式）。**任一文件缺 `from __future__ import annotations` 在 3.9 上就是 latent bug**（运行时 `int | None` 表达式抛 `TypeError: unsupported operand type(s)`）。

r57 之前 `pyproject.toml` 声明 `requires-python = ">=3.9"`，CI matrix 含 `[3.9, 3.12, 3.13]`。3.9 在 GitHub Actions 上的 unit test 是 dummy stub 类型行（不实际触发联合类型 evaluation）所以"看起来过"，但生产路径任何 import 这些模块的代码在 3.9 都会 fail。

## 考虑的方案

1. **降级到 3.9**：所有 7 文件加 `from __future__ import annotations`，恢复 3.9 兼容
2. **bump 到 ≥ 3.10**：`pyproject.toml::requires-python = ">=3.10"`；CI matrix 删 3.9；docs 同步
3. **bump 到 ≥ 3.11**（带 PEP 657 `Self` type）：进一步收紧但削掉 3.10 用户

## 决策

选择**方案 2**：bump 到 ≥ 3.10。

实施：
- `pyproject.toml::requires-python = ">=3.10"`
- `.github/workflows/test.yml::matrix.python-version = ['3.10', '3.12', '3.13']`（CI matrix 6 jobs：2 OS × 3 Python）
- `CLAUDE.md / .cursorrules` "项目身份" 段："Python ≥ 3.10"
- `README.md` / `CONTRIBUTING.md` 全文搜索 "Python 3.9" → "Python 3.10"
- `docs/REFERENCE.md` 同步

## 后果

正面：
- **Latent bug 消除**：PEP 604 语法在生产路径不再依赖 `from __future__` 防御性 import
- 类型注解可读性提升（`int | None` > `Optional[int]`）
- 释放 PEP 612 `ParamSpec`、PEP 647 `TypeGuard`、PEP 654 exception groups 等 3.10 特性供未来使用
- 3.10 是 Ubuntu 22.04 LTS 默认 Python 版本，覆盖率高

负面：
- **BREAKING for 3.9 users**：依赖 3.9 的下游用户失支持。Multi-Engine Game Translator 是个 end-user CLI tool（不是 library），下游用户极少；r57 决策时无 issue 报告 3.9 依赖
- 减少 future Python pin 灵活性（3.11+ specific 语法可写但 CI matrix 受 floor 约束）

## hard contract（#12）

`pyproject.toml requires-python = ">=3.10"`；任何向后兼容 3.9 的 PR 必须先 plan-first（PEP 604 `int | None` 语法已广泛使用，retreating 是大重构）。

## 关联

* 关联 [hard contract #12](../../CLAUDE.md) — Python ≥ 3.10 不可降级
* 关联 r57 audit T1 — 详见 [`_archive/EVOLUTION_r56_r60.md`](../../_archive/EVOLUTION_r56_r60.md) 阶段十六
* 重新引入 3.9 条件：极小概率，需明确用户场景证据 + 7 文件全加 `from __future__ import annotations` + CI matrix 加回 3.9 + 验证 PEP 604 语法在 3.9 都通过 lazy eval（lazy eval 不解析 → 部分类型检查工具会 miss bug）
