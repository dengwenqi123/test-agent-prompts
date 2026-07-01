## [Phase 1/5] 根因分析 — Busy Loop / 死循环

强制**执行**（非仅读取）**skill: crash-analysis** 和 **skill: gdb-start**。在线调试时 gdb 端口在 json 参数 `gdb_port` 中；有 `core_dump_path` 时走 coredump Mode A。**仿真产品（`product=sim*`/`qemu*`）且无 `core_dump_path`/`gdb_port` 但有 `pid`** 时，`pid` 是宿主进程号 → 走 **Mode C**（`attach <pid>`，见 base.agent.md「模式 C」），attach 后用 `info threads`+`bt` 看哪个线程占 CPU，正适合死循环定位。

### Phase 1 出口门禁（不可跳过）

emit 任何根因结论前，**必须**先 emit `## GDB Execution Checkpoint` 块（格式与合法 skip 枚举见 base.agent.md「GDB Execution Checkpoint」章节），且满足以下任一条件：

- `gdb_mode ≠ skipped`（即 A、B 或 C），且 `gdb_connect_done=yes`、`target_done=yes`、`bt_output_present=yes`、`ps_or_info_threads_present=yes`；**或**
- `gdb_mode=skipped` 且 `skip_reason` 命中合法枚举（`no_core_dump_and_no_gdb_port` / `gdb_target_unreachable` / `coredump_load_failed` / `pid_exited_no_core` / `attach_failed`）

`gdb_mode=skipped` 且 `skip_reason` 非法（如「日志已够看死循环」「设备已 reset 不用试」「GDB 会超时」）→ Phase 1 视为未完成，**禁止进入 Phase 2/3**，禁止写 `analysis_report.md`，禁止 `export_patch`。

busyloop 场景特别注意：死循环的根因（退出条件缺失 / 等待事件丢失 / 锁未释放）往往需要 GDB `info threads` + `bt` 看哪个线程占 CPU、等什么信号量/锁——日志只能看现象，GDB 才能定位阻塞链。不得以「日志已显示某线程在跑」为由跳过 GDB。

定位到死循环的可修复根因后，**必须**基于该分析走完 Phase 3/4 产出 patch（见 base.agent.md 核心约束 #1、#10），不允许只给诊断结论收尾。

**自动进入 Phase 2。**
