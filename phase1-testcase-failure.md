## [Phase 1/5] 现场与机制分析 — Test Failure / 测试用例失败

强制**执行**（非仅读取）**skill: crash-analysis** 和 **skill: gdb-start**；`gdb_port` 在输入 JSON 里。**testcase + 仿真产品（`product=sim*`/`qemu*`）且无 `core_dump_path`/`gdb_port` 但有 `pid`** 时，`pid` 是宿主进程号 → 走 **Mode C**（`attach <pid>`，见 base.agent.md「Mode 优先级」「模式 C」），不得以「无 core 无 port」为由直接 skip。

### Phase 1 出口门禁（不可跳过）

按 base.agent.md「GDB Execution Checkpoint」记录取证；字段、合法 skip 枚举与证据要求均复用公共定义，不另设闭集。**取证完成不等于根因正确**；取证未完成须记录实际失败，可补取证或进入 Phase 5 写 `analysis_report.md` 未完成报告，不能绕过门禁导出 patch。

**testcase 场景的 GDB 失效处理（与闭集对齐）：** 测试跑完常触发 `cpu_soft_reset` / 设备重启，socket 文件还在但对端已断。此时**必须先实际尝试** `gdb_connect(port)` + `gdb_command("target remote <gdb_port>")`（或 `bt -1` 探测）；只有当返回 `Remote communication error` / `Target disconnected` / `Broken pipe` 时，才记 `skip_reason=gdb_target_unreachable` 并按 base.agent.md「GDB 失效探测」走源码 fallback。**禁止不尝试就以「设备已 reset」为由跳过 GDB**——「已 reset」不是闭集里的合法 skip_reason，必须通过实际探测落到 `gdb_target_unreachable`。

---

### 双栈分析（testcase 场景核心）

测试失败的根因必须在 **"C 被测程序"** 和 **"pytest 用例脚本"** 两边都读全后再下结论。只看一边容易把"用例期望错"误判成"程序 bug"，反之亦然。

| 层 | 代码位置（`source_root` 下） | 典型表现 |
|---|---|---|
| **被测 C 程序** | `apps/testing/<name>/` / `apps/examples/<name>/` / `frameworks/...` | assert、NULL deref、死循环、返回值错、输出不符 |
| **pytest 用例** | `tests/tools/vtf/tests/...` | 期望 pattern 写错、timeout 过短、fixture 失败、parametrize 错 |
| **VTF 引擎**（可修，见下） | `tests/tools/vtf/{lib,engine,container,configs}/` / `tests/tools/engine/` | 框架级 bug（极少见） |

**分析顺序（推荐）**：
1. 先读 `tests/.../test_<name>.py` — 理解 fixture、期望 pattern、timeout、parametrize
2. 再读被测 C 程序 `_main` 函数全文 — 对比 pytest 期望看实际行为
3. 用文字写出 **"期望 vs 实际"的 diff**，这是根因论证的核心

> 注意：**阅读顺序**（先脚本后程序）与下节的**根因归属顺序**（先被测代码后用例）是两件事。读 pytest 在前是为了拿到"期望契约"，真正判根因时仍按下节优先级。

---

### 根因优先级（Root Cause Priority，硬约束）

> 本节委托 base.agent.md 核心约束 #11 与公共 Phase 2 根因充分性门禁，不覆盖公共规则。优先查交付物是调查顺序，不是发现首个缺陷就停止的归因规则。

- **交付物核查不可跳过**：完整读 `_main` 与相关调用链，核查返回值 / exit code、日志文本/顺序/次数/时序、crash / 竞态 / 资源、配置与设备依赖。读不到的代码如实记为证据缺口
- **契约对照**：核查 pytest pattern、timeout、fixture/setup/teardown、parametrize/marks、断言顺序；由接口/规范/既有正确行为证明契约，不能仅拿当前输出当正确答案
- **因果扩展**：发现 C 异常后仍追踪状态来源、生命周期与时序，可调查相关 fixture、服务、驱动、其他线程/核/系统与 VTF 引擎；多个独立缺陷分别论证，不能预设只有一处根因
- **禁止掩盖问题**：不得跳过交付物核查直接改 pytest，不得为用例通过而放宽断言 / 拉长 timeout / 放松 pattern / 加 skip；没有独立证据不得多层一起改
- **归属与限制**：`diagnosis.root_cause` 的归属前缀、多缺陷和 unknown 表述复用 base #11；归用例或引擎时，报告已核查交付物范围、契约证据、为何解释本次失败及仍未排除因素，不能宣称所有 C 代码无异常

---

### 数据源优先级

1. **`log_path`（full_run_log.txt）** — pytest 输出 + NuttX console 合并日志
2. **`tests/tools/vtf/tests/.../test_<name>.py`** — pytest 源码
3. **`apps/testing/<name>/<name>_main.c`** — 被测 C 程序源码
4. **`elf_path` + `nm`** — 确认被测符号是否在 image 里（见 N1 硬约束）
5. **`gdb_port`** — 优先尝试连接；探测失败（Remote communication error / Target disconnected）时记 `skip_reason=gdb_target_unreachable` 走 1-4 fallback。禁止不探测就跳过

**构建上下文（input_context 若提供则优先用，省去自己 find / 反推）：**
- **`build_config_path`** — 构建实际用的 `.config`。需确认某个 Kconfig 开关时**直接读它**，不要在源码树里 `find .config` / 猜测。例：上次靠它发现 `CONFIG_MBEDTLS_SHA512_ALT=y` 这一关键事实。
- **`build_manifest_path`** — 构建快照 manifest，记录各仓库**构建时真实 commit**。需判断「构建是否含 base 之外的改动（open patch）」时,读它取目标仓库 commit,与 `git -C <repo> rev-parse HEAD` 比对——**替代** `git merge-base` 反推。两者不一致时分两种情况:
  - **本地 checkout 落后**（构建 commit 是远端已合入、只是 source_root 没拉到）⇒ 先调 **`sync_repo(repo_path)`** MCP 工具把该仓库 force-sync 到最新,再重新比对 / 定位代码。sync 后若已 promote 过该仓库,需重新 `promote_repo`。
  - **构建含未合入的 open patch**（sync 后目标 commit 仍不在本地、且无法获取）⇒ 按 N1 走 `source_missing_on_base`，**不要**反复联网 fetch。

---

### 定位源码路径（推荐顺序）

pytest 脚本路径可从 `log_path` / `test_case` 字段直接推出：
- `test_case = "Vela_System_Os_Exception_Crash_Integration"` + `cmd` 里的 `tests/system/os/exception/crash/integration`
  → pytest 在 `tests/tools/vtf/tests/system/os/exception/crash/integration/test_crash_test.py`

C 程序路径：
1. ELF 符号反查：`nm <elf_path> | grep <name>_main` → 找到 `<name>_main` 符号证明程序存在
2. Vela 约定：通常在 `apps/testing/<name>/` 或 `apps/examples/<name>/`
3. git log 回查：`git -C <source_root>/apps log --all --oneline -- 'testing/<name>/**'` 找引入 commit

---

### 现场与契约清单（Phase 1 交接）

逐项附证据与缺口，未完成不得强行打勾；只在公共 Phase 2 通过根因充分性门禁后确认根因。

- [ ] pytest 用例及相关被测 C 函数已完整 Read，记录 fixture、期望 pattern、timeout 与触发路径
- [ ] **知识库检索已完成**：按话题 emit `## Knowledge Base Routing`，diagnose 子报告失败适用 base 内联禁令，不得降级 result 掩盖异常
- [ ] 已写清「期望契约 vs 实际行为」，逐项核查返回值 / 日志 / crash / 竞态 / 资源 / 依赖配置
- [ ] 已记录直接机制、候选原因及反证，旁支缺陷与本次触发链的关联尚未证实则单列，继续调查相关层而非停查
- [ ] **N1 前置**：`git ls-tree <base_ref> <C程序目录>` 和 `git ls-tree <base_ref> <pytest文件>` 都非空；任一为空则进入 Phase 5 报 `source_missing_on_base`、`patch=[]`，禁止重建。其他证据/权限边界也可按公共规则报告停止

---

### 🛠 修复范围

本 Agent 在 testcase 场景可修改以下三类代码：

| ✅ 可修 | 示例 |
|---|---|
| 被测 C 程序 | `apps/testing/crash_test/crash_test_main.c` |
| pytest 用例脚本 | `tests/tools/vtf/tests/system/os/exception/crash/integration/test_crash_test.py` |
| VTF 引擎代码 | `tests/tools/vtf/{lib,engine,container,configs}/**`、`tests/tools/engine/**` |

**根因归属、候选提交与结果协议均复用 base.agent.md** 核心约束 #10/#11、Phase 2/3 门禁与 Phase 5 示例；找到局部缺陷不强制产 patch，N1 不是唯一允许无候选的原因。

若有充分证据归因到 VTF 引擎，先按公共 Phase 3 设计与验证，再决定是否进入 Phase 4；提交前仍须 promote。`diagnosis.root_cause` 用 `vtf_engine_bug: <位置与契约原因>`，未证实归属则如实写 unknown。`status` 仅用 `patch_generated` / `failed_to_fix`；`patch` 沿用公共的仓库对象数组，无候选统一 `[]`，不另设字符串 diff 示例。

⚠️ **VTF 是所有 CT 测试的共享基础设施**，改一次影响所有用例。修改时务必：
- 保持最小修改，不做无关重构
- 不破坏既有用例的契约（pattern / timeout / fixture 行为）
- 在 `analysis_report.md` 中明确说明影响范围与回归风险

---

**按 base.agent.md 公共 Phase 2 根因充分性门禁 → Phase 3 修复设计与验证 → Phase 5 报告推进；证据不足可报告停止，不强制产 patch。**
