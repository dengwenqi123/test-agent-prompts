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
- [ ] 被测 C 程序 `_main` 函数已完整 Read（禁止只看片段凭函数名猜）
- [ ] **"pytest 期望 vs C 程序实际输出"的 diff 已用文字写清楚**
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
