## [Phase 1/5] 现场与机制分析 — Crash / 异常崩溃

强制**执行**（非仅读取）**skill: crash-analysis** 和 **skill: gdb-start**。在线调试时 gdb 端口在 json 参数 `gdb_port` 中；有 `core_dump_path` 时走 coredump Mode A。

> ⚠️ **顺序覆盖声明**：crash-analysis SKILL.md 写「Both → 先 Log 概览再 GDB 深入」，**本项目作废此顺序**。当 `core_dump_path` 存在时，**先 GDB Mode A 再 Log 分析**（理由：Log-then-GDB 会让 agent 做完 Log 即收尾、跳过 GDB，已发生过实际 violation）。skill 文本与本句冲突时，以本句为准。Log 模式补充输入、状态变化、错误传播及同核/跨核时间线，但不能替代应做的 GDB 取证。

### Phase 1 出口门禁（不可跳过）

按 base.agent.md「GDB Execution Checkpoint」记录取证，字段（含 `ps_or_info_threads_present`）、合法 skip 枚举与证据要求均复用公共定义，不另设闭集。**取证完成不等于根因正确**；取证未完成须如实记录，可补取证或进入 Phase 5 写 `analysis_report.md` 未完成报告，不能伪造根因、绕过门禁导出 patch。

当 `core_dump_path` 存在时，按 base.agent.md「Mode 优先级」**先 GDB Mode A 再 Log 分析**，不得用 Log 模式替代 GDB。

### 现场与直接机制

记录异常指令/栈帧、触发条件、对象与参数的实际状态、错误传播路径，区分原始输出、源码事实与推断。NULL deref / 越界 / assert 是直接机制或局部缺陷线索，不自动解释无效状态为何形成；把候选原因、反证与缺失证据交给公共 Phase 2 因果回溯。

### 根因归属（crash 由测试用例触发时适用）

输入含 `test_case` 时，按 base.agent.md 核心约束 #11 优先核查交付物并读取测试契约；不得因 crash 就预设 C 侧有罪，也不得发现一个 C 异常就停止相关依赖调查。禁止通过放宽断言 / 拉长 timeout / 放松 pattern / 加 skip 掩盖问题；多缺陷与 unknown 如实报告。

**按 base.agent.md 公共 Phase 2 根因充分性门禁 → Phase 3 修复设计与验证 → Phase 5 报告推进；证据不足可报告停止，不强制产 patch。**
