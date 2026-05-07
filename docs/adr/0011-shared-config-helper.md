# 0011. `_resolve_args_from_config` shared config helper

* 状态：Accepted
* 引入轮次：r58 A1
* 决策者：@Dean20030514
* 关联：[`core/config.py::resolve_args_from_config`](../../core/config.py) / [`docs/REFERENCE.md §7a`](../REFERENCE.md)

## 背景

r58 之前 `main.py::main()` L249-266 inline 三层合并代码（CLI args > config file > defaults）：

```python
# 三层合并 inline pseudo-code（r57 末状态）
config = json_load(config_path) if config_path else {}
args.api_key = args.api_key or config.get("api_key") or os.environ.get("LLM_API_KEY") or DEFAULT_API_KEY
args.provider = args.provider or config.get("provider") or DEFAULT_PROVIDER
# ... 20+ 字段类似处理
```

问题：
- GUI / one-click pipeline 等其他 entry point 想复用 → 必须 copy-paste
- 改 config 字段需扫所有 entry point 同步改
- 顺序敏感（CLI > config > env > default）写错一处难发现

## 考虑的方案

1. **inline 不动**：每个 entry point 自维护一份合并逻辑（status quo）
2. **抽取共享 helper**：`core/config.py::resolve_args_from_config(args, cfg)` 作为唯一 source of truth
3. **改用 dataclass + `__post_init__`**：彻底重构 args 为 immutable struct（架构大改）

## 决策

选择**方案 2**：抽取共享 helper。

实施（r58 A1）：
- 新 `core/config.py::resolve_args_from_config(args: argparse.Namespace, cfg: dict) -> argparse.Namespace`
  - 接受 CLI args + 已 load 的 config dict
  - 返回 args（in-place 修改后的）— 三层合并完成
  - ~70 行
- `main.py::main()` 调用：`args = resolve_args_from_config(args, cfg)` 替代原 inline 块
- 单元测试 `tests/test_main_cli.py::test_w_round58_a1_*`：
  - `fills_defaults`：empty args → 全填默认
  - `target_lang_hardcoded_zh`：r52 C4 contract 验证（target_lang 永远是 "zh"）

## 后果

正面：
- **单一 source of truth**：改 config 逻辑只改 `core/config.py` 一处
- 未来 entry point（GUI in-process / future REST API server / etc.）可直接 import + reuse
- 测试覆盖（2 单元测试）作 regression contract

负面：
- 当前**实际 reuse 仅 main.py**（GUI 仍走 subprocess.Popen，见 [r60 audit A2](../../AUDIT_R57.md)）— helper 现 single-caller，看起来过度抽象
- 增加一次 function call 开销（微秒级，可忽略）

中立：
- 与 [ADR 0004](0004-renpy-stays-on-dedicated-pipelines.md) 不冲突：config 解析层是 entry point 共享，pipeline 层各自专有

## architectural decision（不是 hard contract）

`_resolve_args_from_config` 是 architectural pattern，不是 hard contract。约束较弱：
- 新 entry point **应该** 优先 reuse helper（ADR 推荐）
- 不强制（GUI subprocess 模式有正当理由保持 — 见 [r60 audit A2 retire](../../AUDIT_R57.md)）

## 关联

* 关联 r58 audit A1 — 详见 [`_archive/EVOLUTION_r56_r60.md`](../../_archive/EVOLUTION_r56_r60.md) 阶段十七
* 关联 r60 audit A2 — GUI subprocess.Popen 间接调用未真正 reuse helper（retire to architectural decision）
* 关联 [docs/REFERENCE.md §7a](../REFERENCE.md) — 配置层级优先级文档
* 重构条件：未来 GUI 改为 in-process 模式时，helper 真正 cross-entry-point 复用，价值显现
* retire 条件：连续 ≥3 个新 entry point 都选 subprocess.Popen 而非 import helper，证明该 pattern 实际未发挥价值，可降级为 main.py-private inline
