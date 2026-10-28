## [Phase 1/5] 现场与机制分析 — Busy Loop / 死循环

强制**执行**（非仅读取）**skill: crash-analysis** 和 **skill: gdb-start**。在线调试时 gdb 端口在 json 参数 `gdb_port` 中；有 `core_dump_path` 时走 coredump Mode A。**仿真产品（`product=sim*`/`qemu*`）且无 `core_dump_path`/`gdb_port` 但有 `pid`** 时，`pid` 是宿主进程号 → 走 **Mode C**（`attach <pid>`，见 base.agent.md「模式 C」），attach 后用 `info threads`+`bt` 看哪个线程占 CPU，正适合死循环定位。

### Phase 1 出口门禁（不可跳过）

按 base.agent.md「GDB Execution Checkpoint」记录取证；字段、合法 skip 枚举与证据要求均复用公共定义，不另设闭集。**取证完成不等于根因正确**；取证未完成须记录实际失败，可补取证或进入 Phase 5 写 `analysis_report.md` 未完成报告，不能绕过门禁导出 patch。

busyloop 场景先记录运行/等待线程、循环条件、信号量/锁与事件状态。GDB `info threads` + `bt` 帮助定位阻塞链，日志补充事件发生与丢失的时间线；单次栈快照不证明一直占 CPU，也不证明事件从未发生。不得以「日志已显示某线程在跑」为由跳过 GDB。

### 根因归属（busyloop 由测试用例触发时适用）

输入含 `test_case` 时，按 base.agent.md 核心约束 #11 优先核查交付物（退出条件、等待事件、锁释放、超时处理），结合测试契约继续追踪相关生产者/消费者和跨层依赖。局部异常不自动终止归因；允许多缺陷与 unknown。禁止靠拉长 `timeout` 或放宽断言掩盖真死循环。

**按 base.agent.md 公共 Phase 2 根因充分性门禁 → Phase 3 修复设计与验证 → Phase 5 报告推进；证据不足可报告停止，不强制产 patch。**
