## [Phase 1/5] 根因分析 — Busy Loop / 死循环

强制使用 **skill: crash-analysis** 和 **skill: gdb-start** 分析异常,这是在线调试，gdb 的端口 在 json 参数 gdb_port 中。

定位到死循环的可修复根因（退出条件缺失 / 等待事件丢失 / 锁未释放等）后，**必须**基于该分析走完 Phase 3/4 产出 patch（见 base.agent.md 核心约束 #10），不允许只给诊断结论收尾。

**自动进入 Phase 2。**
