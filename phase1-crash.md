## [Phase 1/5] 根因分析 — Crash / 异常崩溃

强制**执行**（非仅读取）**skill: crash-analysis** 和 **skill: gdb-start**。在线调试时 gdb 端口在 json 参数 `gdb_port` 中；有 `core_dump_path` 时走 coredump Mode A。

> ⚠️ **顺序覆盖声明**：crash-analysis SKILL.md 写「Both → 先 Log 概览再 GDB 深入」，**本项目作废此顺序**。当 `core_dump_path` 存在时，**先 GDB Mode A 再 Log 分析**（理由：Log-then-GDB 会让 agent 做完 Log 即收尾、跳过 GDB，已发生过实际 violation）。skill 文本与本句冲突时，以本句为准。Log 模式仅用于补充 GDB 看不到的跨核时间线。

### Phase 1 出口门禁（不可跳过）

emit 任何根因结论前，**必须**先 emit `## GDB Execution Checkpoint` 块（格式与合法 skip 枚举见 base.agent.md「GDB Execution Checkpoint」章节），且满足以下任一条件：

- `gdb_mode ≠ skipped`（即 A、B 或 C），且 `gdb_connect_done=yes`、`target_done=yes`、`bt_output_present=yes`、`ps_output_present=yes`；**或**
- `gdb_mode=skipped` 且 `skip_reason` 命中合法枚举（`no_core_dump_and_no_gdb_port` / `gdb_target_unreachable`；仿真产品无 core/port 走 Mode C 时另可命中 `pid_exited_no_core` / `attach_failed`）

`gdb_mode=skipped` 且 `skip_reason` 非法（如「根因在另一核」「无对端核 ELF」「日志已足够」）→ Phase 1 视为未完成，**禁止进入 Phase 2/3**，禁止写 `analysis_report.md`，禁止 `export_patch`。

当 `core_dump_path` 存在时，按 base.agent.md「Mode 优先级」**先 GDB Mode A 再 Log 分析**，不得用 Log 模式替代 GDB。

定位到 crash 的可修复根因（NULL deref / 越界 / 资源泄漏 / 竞态等）后，**必须**基于该分析走完 Phase 3/4 产出 patch（见 base.agent.md 核心约束 #1、#10），不允许只给诊断结论收尾。

**自动进入 Phase 2。**
