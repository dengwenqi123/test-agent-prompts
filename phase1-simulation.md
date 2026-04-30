## [Phase 1/5] 根因分析 — Simulation / 流程冒烟验证

> ⚠️ **本次 session 是 non-LLM 流水线的端到端冒烟测试，不是真实修复任务。**
> 本 phase1 **覆盖** base.agent.md 里"必须使用 crash-analysis / gdb-start skill"的核心约束 #1。
> **不要**调用 `mcp__gdb-mcp__*` 任何工具，**不要**读 `crash-analysis` / `gdb-start` skill，**不要**分析 `log_path` / `elf_path` / `core_dump_path`。
> 目标是验证 **workspace setup → promote → commit → export_patch → FDS 上传 → callback** 这条非推理链路稳定可靠。

---

### 本次 session 的固定"修复"动作

不做任何分析，直接在 `tests` 仓库的 `testcases/kvtest/` 目录下挑**一个已存在的源文件**，在文件末尾追加一个**空行**。这样产生一个最小、可验证、零语义风险的 diff，走完整 git / FDS / callback 链路。

### 根因（固定话术）

```
simulation: non-LLM pipeline smoke test, no real defect analysis performed
```

这一段会原样填到 Phase 5 的 `diagnosis.root_cause`。

---

### 执行步骤（照做）

**1. 定位改动目标**

用 `git ls-tree` 列出 `testcases/kvtest/` 下的真实文件（不要 `find`，不要 `ls` workspace symlink）：

```bash
git -C {source_root}/tests ls-tree -r --name-only vela/dev-system testcases/kvtest/ | head -10
```

挑**第一个 `.c` 文件**作为目标。记下相对 `tests` 仓库根的路径，例如 `testcases/kvtest/foo.c`。

**2. 验证文件存在于 base**（N1 前置）

```bash
git -C {source_root}/tests ls-tree vela/dev-system testcases/kvtest/<file>.c
```

如果为空（不存在）→ 换一个 `.c` 文件；若 `testcases/kvtest/` 整个目录在 base 上都不存在 → 进 Phase 5 报 `status=failed_to_fix`, `diagnosis.root_cause="source_missing_on_base: testcases/kvtest not in vela/dev-system"`，**不要**凭空创建。

**3. 直接进入 Phase 2**

本 session 的 Phase 2 也是极简：读取目标文件确认它能被 Read（≤ 50 行即可，不需要完整读全），然后进入 Phase 3。

---

### ✅ 这条 session 保留的硬约束

- ✅ `source_root` 只读（严禁修改）
- ✅ Git 操作必须走 MCP 工具（`promote_repo` / `commit_in_workspace` / `export_patch`）
- ✅ commit 必须在 `ai-fix/<topic>-<sid>` 分支上（**禁止**直接 commit 到 `dev-system` 等保护分支）
- ✅ commit message 包含 JIRA trailer，subject 不能 JIRA-prefix
- ✅ Phase 5 必须写 `ai_debug_result.json` 和 `analysis_report.md`，并通过 callback 上报 VTF

### ❌ 这条 session 跳过的工作

- ❌ GDB 连接、`gdb_port` / `gdb_script` 字段忽略
- ❌ crash-analysis skill / gdb-start skill
- ❌ ELF 符号查（`nm`、`addr2line`）
- ❌ log_path 解析 / 根因推理 / 源码深度阅读
- ❌ AI 自检 7 项（空行改动无实质逻辑，自检格式化走过场即可）

---

### Phase 3/4/5 补充说明（同真实流程）

Phase 3 修复目标分支（仍然必须）：
```bash
# 在 workspace 的 tests 仓库里
git checkout -b ai-fix/simulation-{sid} vela/dev-system
```

commit message 模板（请按此格式写，替换 `{target_file}` 为实际路径）：
```
simulation: append blank line to {target_file}

Automated smoke test for ai-agent-service non-LLM pipeline:
workspace / promote / commit / export_patch / FDS / callback.
This diff has no functional effect — it appends a single
trailing newline to a pre-existing test source file so the
end-to-end plumbing can be exercised on real infrastructure
without touching production logic.

JIRA: VELAPLATFO-89716
```

Phase 4 的 `commit_in_workspace` 传 `files=["testcases/kvtest/<file>.c"]`。
Phase 4.2 `export_patch` / Phase 5 `ai_debug_result.json` 完全同真实流程，`status="patch_generated"`，`diagnosis.exception_type="simulation"`，`diagnosis.confidence="high"`。

---

**自动进入 Phase 2。**
