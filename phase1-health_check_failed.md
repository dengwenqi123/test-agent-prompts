## [Phase 1/5] 现场与机制分析 — Health Check Failed / 重启健康检查异常

设备在重启/健康检查阶段诊断出异常。输入 JSON 的 `diagnose_report` 字段携带了各项诊断子报告，是本次分析的**首要线索**，必须先解析它再决定后续调查方向。

### 1. 解析 diagnose_report（必做，优先于 GDB）

`diagnose_report` 是一个数组，每个元素形如：

```json
{
  "title": "tlsdump report",
  "summary": "integrity check",
  "result": "failed",        // pass | fail | failed
  "category": "system",       // sched | system | connectivity | ...
  "command": "tlsdump",       // 诊断命令
  "data": "..."               // 命令原始输出（字符串或数组，可能为空）
}
```

分析步骤：
1. 逐条读取，**筛出 `result ∈ {"fail", "failed"}` 的子报告**（两种取值都计为失败，只筛 "failed" 会漏掉 "fail" 项）—— 这些是根因的直接候选。
2. 对每个失败项，结合 `category` / `command` / `data` 判断故障子系统（如 `sched` 死锁、`system` 完整性、`connectivity` socket 泄漏）。
3. `result == "pass"` 仅是该检查覆盖范围、采样时刻和前提内的阴性证据，不能全局排除该类故障（例如死锁报告 pass 不排除其他时刻、线程或未覆盖路径的死锁）。
4. `extra_context.state_reason` 通常给出触发原因（如 `Reboot diagnose found issues`）。

> ⚠️ 筛出失败子报告后，**先按 base.agent.md「知识库检索（Knowledge Base Routing）」完成匹配**再分析：diagnose 子报告失败（mm leak / memcheck 等）必读 `common_knowledge/debugging/diagnose_failure_analysis.md`，按其规则逐失败项做可审计结论（verdict 表）。**禁止以把子报告 `result` 从 `fail` 降级为 `warn`/`pass` 作为修复**（含修改 nxgdb 诊断工具的 result 判定）——消费方只认 fail，降级等于静默清除告警；`alive=false` 的块是常见真泄漏形态，不是误报信号。

### 2. 结合 GDB / 日志深入定位

若 `diagnose_report` 不足以定位到源码，且提供了 `gdb_port` / `gdb_rpc_host` / `gdb_rpc_port`，这是在线调试：

- 强制使用 **skill: crash-analysis** 和 **skill: gdb-start** 连接设备做进一步分析。
- 非本机时用 `mcp__gdb-mcp__gdb_connect(host=<gdb_rpc_host>, port=<gdb_rpc_port>)`。
- 若 GDB 对端已失效（socket 在但设备已重启），按 base 里的「GDB 失效探测」切换到 `log_path` + `elf_path` 源码 fallback。

无论子报告是否已指向源码，都按 base.agent.md「GDB Execution Checkpoint」执行适用取证；字段、合法 skip 枚举与证据要求复用公共定义。**取证完成不等于根因正确**；取证失败可补取证或进入 Phase 5 写 `analysis_report.md` 未完成报告，不得伪造根因或绕过门禁导出 patch。

分析结论必须对应到 `diagnose_report` 的失败项，先记录现场、机制与证据范围，再追踪状态形成原因；多个失败项可有不同贡献原因，不强行合并。`diagnosis.exception_type` 填 `health_check_failed`；含 `test_case` 时同样遵循 base #11 的交付物优先核查与契约归因。

**按 base.agent.md 公共 Phase 2 根因充分性门禁 → Phase 3 修复设计与验证 → Phase 5 报告推进；证据不足可报告停止，不强制产 patch。**
