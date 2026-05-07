# 0008. Path traversal 防护 — `_FORBIDDEN_PATH_PREFIXES`

* 状态：Accepted
* 引入轮次：r57 S2
* 决策者：@Dean20030514
* 关联：[`main.py::_FORBIDDEN_PATH_PREFIXES`](../../main.py) / [hard contract #13](../../CLAUDE.md)

## 背景

r57 S2 audit 评估 path traversal 风险：用户传 `--game-dir` / `--config` 参数，若恶意指向 `/etc/passwd` / `c:/windows/system32/...` / 等系统目录，pipeline 可能：
- 写入翻译产物到系统目录（污染）
- 读取系统配置作为"游戏文件"（信息泄露 via LLM API）
- 备份机制 `.bak` 写入系统目录（覆盖系统文件）

威胁模型：
- **本地 single-user 工具**：用户自己运行自己电脑上的工具，攻击者已经能访问 `~/.bashrc` 的话已经 game over → 此面 threat 不强
- **多用户共享环境**：CI runner / 教学实验室 / 共享桌面，user A 给 user B 一个恶意 `renpy_translate.json` 含 `--game-dir /etc/`，B 在不审 config 时被骗 → defense-in-depth 必要

## 考虑的方案

1. **不防护**：信任用户输入（与"本地 single-user"威胁模型一致）
2. **黑名单系统目录前缀**：拒绝 resolve 到 `/etc/` `/proc/` `c:/windows/` 等的路径
3. **白名单允许目录**：仅允许特定前缀（更严但用户体验差）

## 决策

选择**方案 2**：黑名单系统目录前缀（`_sanitize_user_path` helper + `_FORBIDDEN_PATH_PREFIXES` 列表）。

实施：
- `main.py::_FORBIDDEN_PATH_PREFIXES` 列表：
  - Unix: `/etc/`, `/sys/`, `/proc/`, `/dev/`, `/root/`, `/boot/`, `/var/log/`
  - Windows: `c:/windows/`, `c:/program files/`, `c:/programdata/`, etc.
- `main.py::_sanitize_user_path(path)`：`Path(path).resolve()` 后小写化对比，命中前缀 → `raise ValueError`
- 入口处调用：`--game-dir`, `--config`, `--writeback-dir` 等所有 user-supplied path
- 3 测试覆盖（forbidden resolved path / Windows System32 mock / legitimate user path）

## 后果

正面：
- **defense-in-depth**：本地威胁模型不变（用户跑自己游戏目录），但多用户共享环境获得保护
- 防止合法用户意外（typo `--game-dir /etc` 而非 `~/games/etc`）
- 错误信息明确（`PathTraversalError: refusing to operate on system path`），用户立即定位
- `.bak` 备份不会污染系统目录

负面：
- 极小概率合法用户场景被拒（如某用户有合法理由读 `/var/log/`）— 现实中 0 报告
- 黑名单需维护新系统路径（如未来 Linux 加 `/snap/` 之类）

中立：
- 不阻止用户 symlink 绕过（symlink resolution 后判断，所以 `~/safe -> /etc/` 也会被拒；这是 feature 不是 bug）

## hard contract（#13）

`main.py::_FORBIDDEN_PATH_PREFIXES` 不可放宽；任何添加 user-supplied path 入口必须经过 `_sanitize_user_path`；本地 single-user 工具威胁模型不变，但多用户共享环境的 defense-in-depth 不可缺。

## 关联

* 关联 [hard contract #13](../../CLAUDE.md) — Path traversal 防护契约
* 关联 r57 audit S2 — 详见 [`_archive/EVOLUTION_r56_r60.md`](../../_archive/EVOLUTION_r56_r60.md) 阶段十六
* 放宽 `_FORBIDDEN_PATH_PREFIXES` 条件：必须先 plan-first 论证用户场景；放宽后所有调用 `_sanitize_user_path` 的入口必须重新 audit
* 扩展条件：新入口（如 `--screen-dir`）加进 user-supplied path family 必须 wrap 一次 `_sanitize_user_path` 调用，单元测试覆盖 forbidden case
