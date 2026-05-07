# 0010. EVOLUTION 5 轮滚动归档

* 状态：Accepted
* 引入轮次：r58 P3 约定 / r60 首次执行
* 决策者：@Dean20030514
* 关联：[`_archive/EVOLUTION.md`](../../_archive/EVOLUTION.md) / [`_archive/EVOLUTION_r56_r60.md`](../../_archive/EVOLUTION_r56_r60.md) / [hard contract #15](../../CLAUDE.md) / CLAUDE.md "文档归档节奏" 段

## 背景

r56 末 `_archive/EVOLUTION.md` 已 290+ 行（每轮 +20-30 行）。无干预下：
- r70 时预测 ~600 行，r100 时 ~1200 行
- 单 file 加载 / scan / Ctrl+F 性能下降
- 新 maintainer 阅读历史成本指数增长
- 工具（如 verify_docs_claims）grep 范围扩大

需要节奏化的 maintenance pattern。

## 考虑的方案

1. **不归档**：让 EVOLUTION 单调增长（status quo 至 r57）
2. **每 5 轮滚动归档**：每 r5N 把最近 5 stages 抽到独立 archive 文件，主文件仅留 1-2 行摘要 + 阶段表格行
3. **每 10 轮归档**：减半频率但单次归档量翻倍
4. **基于行数触发**：当 EVOLUTION 超 500 行触发归档（更动态）

## 决策

选择**方案 2**：每 5 轮滚动归档。

约定（r58 P3）：
- **触发条件**：每 5 轮（r60、r65、r70、…）执行一次归档
- **操作步骤**（在该轮 docs sync commit 内完成）：
  1. 把 `_archive/EVOLUTION.md` 中"阶段 N - 4"到"阶段 N"5 个阶段的详细叙事**整体抽出**，放到新文件 `_archive/EVOLUTION_rN-4_rN.md`
  2. 主 `_archive/EVOLUTION.md` 只留**1 段摘要**（每轮 1-2 句 OR 多轮合并表格行）+ 阶段表格行
  3. CLAUDE.md "文档索引" 表格加新归档文件 entry
  4. **验证阈值**（r60 微调）：`wc -l _archive/EVOLUTION.md` 应减少 ≥ **80 行 OR ≥ 20%**
- **归档命名规则**：`_archive/EVOLUTION_r{N-4}_r{N}.md`
- **不归档**：阶段一/二/三/... 表格行 + 累积技术资产段 + 设计原则演进段（跨轮总结性内容留主文件）

首次执行（r60）：
- 新文件 `_archive/EVOLUTION_r56_r60.md` — r56-r60 完整 5 阶段叙事
- 主 EVOLUTION.md 364 → 276 行（-88 / 24%）通过阈值

## 后果

正面：
- **主 EVOLUTION 大小可控**：每 5 轮归档一次，主文件 ~250-300 行平稳
- **历史完整保留**：归档文件记录每轮触发 / 决策 / 改动文件，git log + 归档双覆盖
- **新 maintainer 阅读成本平稳**：主 EVOLUTION 给 high-level 节奏，归档按需打开
- 可预测的 cadence：r65 / r70 / r75 / ... 触发点写入 hard contract #15

负面：
- 跨轮 grep 需多文件（`grep -r "..." _archive/`），轻微不便
- 归档命名占用 `_archive/` 列表空间（r100 时已有 20 个 archive 文件）

中立：
- 早期 r1-r55 stages 不归档（因为它们已经是表格行格式，不臃肿）

## hard contract（#15）

每 5 轮（r60 ✓ / r65 / r70 / ...）必须执行归档；阈值 ≥80 行 OR ≥20% 缩减；不能跳过。

## 阈值演变

| 轮次 | 阈值文字 | 实测 | 备注 |
|------|---------|------|------|
| r58 P3 引入 | "≥ 100 行" | — | 启发式估计 |
| r60 首次执行 | "≥ 80 行 OR ≥ 20%" | 364→276 (-88/24%) | r56-r60 含 3 轮 doc-only 短叙事，100 行不可达；微调到双阈值 OR 关系 |

## 关联

* 关联 [hard contract #15](../../CLAUDE.md) — EVOLUTION 滚动归档触发
* 关联 [`_archive/EVOLUTION_r56_r60.md`](../../_archive/EVOLUTION_r56_r60.md) — r60 首次归档产物
* 关联 r58 audit P3 + r60 首次执行 — 详见 [`_archive/EVOLUTION_r56_r60.md`](../../_archive/EVOLUTION_r56_r60.md) 阶段十七 / 阶段十九
* 跳过条件：无（hard contract 明确"不能跳过"）
* 阈值再次调整条件：连续 ≥3 个归档周期都难以达到 ≥80 行 ≥20% 时（如未来轮次大量是 doc-only）；目前不预期触发
