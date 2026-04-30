## [Phase 1/5] 根因分析 — Test Failure / 测试用例失败

强制使用 **skill: crash-analysis** 和 **skill: gdb-start** 分析；`gdb_port` 在输入 JSON 里。
若 GDB 连接失败（Remote communication error / Target disconnected），按 base.agent.md 的"GDB 失效探测"章节走源码 fallback。

---

### 双栈分析（testcase 场景核心）

测试失败的根因必须在 **"C 被测程序"** 和 **"pytest 用例脚本"** 两边都读全后再下结论。只看一边容易把"用例期望错"误判成"程序 bug"，反之亦然。

| 层 | 代码位置（`source_root` 下） | 典型表现 |
|---|---|---|
| **被测 C 程序** | `apps/testing/<name>/` / `apps/examples/<name>/` / `frameworks/...` | assert、NULL deref、死循环、返回值错、输出不符 |
| **pytest 用例** | `tests/tools/vtf/tests/...` | 期望 pattern 写错、timeout 过短、fixture 失败、parametrize 错 |
| **VTF 引擎**（🛑 禁改，见下） | `tests/tools/vtf/{lib,engine,container,configs}/` / `tests/tools/engine/` | 框架级 bug（极少见） |

**分析顺序（推荐）**：
1. 先读 `tests/.../test_<name>.py` — 理解 fixture、期望 pattern、timeout、parametrize
2. 再读被测 C 程序 `_main` 函数全文 — 对比 pytest 期望看实际行为
3. 用文字写出 **"期望 vs 实际"的 diff**，这是根因论证的核心

> 注意：**阅读顺序**（先脚本后程序）与下节的**根因归属顺序**（先被测代码后用例）是两件事。读 pytest 在前是为了拿到"期望契约"，真正判根因时仍按下节优先级。

---

### 根因优先级（Root Cause Priority，硬约束）

**默认假设根因在被测代码（项目代码）侧**。只有当被测代码经完整核查确认无异常后，才允许把根因归到测试用例本身。

**顺序不可颠倒的理由**：
- 被测代码是交付物，用例是验收手段；交付物有 bug 的概率远高于验收手段
- 先怀疑用例容易"改用例掩盖真 bug"（把 assert 放宽、timeout 拉长、pattern 改松），让回归用例失去护栏作用
- 用例问题通常表现为"期望/触发/匹配"的 contract 偏差，而非功能性错误；只有在被测代码侧找不到对得上的异常行为时，这种偏差才是真根因

**两步判定**：

1. **Step 1 — 被测代码侧核查**（必须先做，不可跳过）
   - 完整读 `_main` 及被触发的全部调用链（禁止只看片段）
   - 核对以下潜在问题：
     - 返回值 / 错误码 / exit code 是否与用例期望一致
     - 打印/日志的**文本、顺序、次数、时序**是否与 pytest 期望的 pattern 吻合
     - 是否存在 crash / assert / NULL deref / 越界 / 资源泄漏 / 死循环
     - 是否存在竞态（race）、未初始化、未处理的 errno / signal
     - 依赖的配置、Kconfig、设备节点是否齐全
   - 若发现任一问题 → **根因归属被测代码**，进入 Phase 2/3 修 C 程序；不再继续 Step 2
   - 若确认被测代码行为完全符合"被测意图"（功能正确），再进入 Step 2

2. **Step 2 — 测试用例侧核查**（仅在 Step 1 通过后执行）
   - 逐项核查 pytest 脚本：
     - 期望的 pattern / 正则是否贴合被测程序的真实输出（大小写、空格、换行、多行模式）
     - `timeout` 是否过短（尤其慢板子 / 冷启动 / 首次加载）
     - fixture / setup / teardown 的前置条件是否满足（mount、网络、设备节点）
     - `parametrize` 参数集合、`marks`、`skip_if` 是否正确
     - 断言顺序与实际日志产生顺序是否一致（async 场景特别注意）
   - 若发现问题 → 根因归属测试用例，修 pytest 脚本

**禁止行为（violation）**：
- ❌ 跳过 Step 1 直接改 pytest 脚本
- ❌ 以"用例期望写得不合理"为由放宽断言，而未先确认被测代码的实际行为是否本该如此
- ❌ 在 Step 1 未完成时并行修两边（双改会掩盖真根因，且引入回归盲区）
- ❌ 仅凭函数名或日志片段就断定"用例 pattern 写错"，未完整读被测 `_main` 和调用链

**写入 Phase 5 `diagnosis.root_cause` 时必须明确归属**：
- 被测代码侧：`testee_bug: <file>:<line> <一句话根因>`
- 测试用例侧：`testcase_bug: <test_file>:<line> <一句话根因>`（且需在 analysis_report 中说明"已确认被测代码行为正确"的依据）

---

### 数据源优先级

1. **`log_path`（full_run_log.txt）** — pytest 输出 + NuttX console 合并日志
2. **`tests/tools/vtf/tests/.../test_<name>.py`** — pytest 源码
3. **`apps/testing/<name>/<name>_main.c`** — 被测 C 程序源码
4. **`elf_path` + `nm`** — 确认被测符号是否在 image 里（见 N1 硬约束）
5. **`gdb_port`** — 设备未 reset 时可用；已 reset 时跳过，用 1-4 fallback

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

### 根因定位清单（Phase 1 完成前必须全打勾）

- [ ] pytest 用例文件已完整 Read，记录：fixture 行为、期望 pattern、timeout 秒数
- [ ] 被测 C 程序 `_main` 函数及被触发调用链已完整 Read（禁止只看片段凭函数名猜）
- [ ] **"pytest 期望 vs C 程序实际输出"的 diff 已用文字写清楚**
- [ ] **Step 1（被测代码侧）已完成**：返回值 / 日志 / crash / 竞态 / 资源 / 依赖配置逐项核查
  - 若发现被测代码异常 → `root_cause` 归属 `testee_bug:...`，**跳过 Step 2**
- [ ] **Step 2（测试用例侧）仅在 Step 1 确认无异常后执行**：pattern / timeout / fixture / parametrize / 断言顺序逐项核查
  - 归属 `testcase_bug:...` 时，analysis_report 必须说明"已确认被测代码行为正确"的依据
- [ ] **N1 前置**：`git ls-tree <base_ref> <C程序目录>` 和 `git ls-tree <base_ref> <pytest文件>` 都非空
  若任一为空 → 立即进入 Phase 5 报 `source_missing_on_base`

---

### 🛑 修复边界（硬约束）

本 Agent 在 testcase 场景**只修两类代码**：

| ✅ 可修 | 示例 |
|---|---|
| 被测 C 程序 | `apps/testing/crash_test/crash_test_main.c` |
| pytest 用例脚本 | `tests/tools/vtf/tests/system/os/exception/crash/integration/test_crash_test.py` |

**🛑 禁止修改 VTF 引擎代码**（测试框架共享基础设施）：

| 禁改路径 | 说明 |
|---|---|
| `tests/tools/vtf/lib/**` | VTF 库（async_event / crash.py / detector 等） |
| `tests/tools/vtf/engine/**` | VTF 运行引擎 |
| `tests/tools/vtf/container/**` | 容器 / overlay |
| `tests/tools/vtf/configs/**` | VTF 运行时配置 |
| `tests/tools/vtf/docs/**` | 文档 |
| `tests/tools/engine/**` | 兄弟 engine 目录（framework/libs 等） |

**理由**：
- VTF 是所有 CT 测试的共享基础设施，改一次影响所有用例
- 本 Agent 目标是**修具体 testcase 的 bug**，不是维护框架
- 引擎 bug 归属框架团队，不属于 autofix 范围

**如果根因定位到 VTF 引擎**：不要动手修，直接进入 Phase 5 写：
```json
{
  "status": "failed_to_fix",
  "diagnosis": {
    "root_cause": "vtf_engine_bug: <具体位置:行号> <现象描述>",
    "exception_type": "testcase",
    "confidence": "high"
  },
  "patch": []
}
```
由人工判断框架侧修复路径。

---

**自动进入 Phase 2。**
