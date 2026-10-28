# test-agent-prompts

嵌入式异常分析与候选修复提示词。仓库中的调试、提交、导出、回调示例是 **prompt 数据**，维护/静态检查时不要执行。

## 装配与入口

读取 `base.agent.md`，按异常类型选取**一份**入口全文替换其中唯一的 `{{PHASE1}}`，再由宿主注入实际输入上下文：

| 类型 | Phase 1 文件 |
|---|---|
| crash | `phase1-crash.md` |
| busyloop | `phase1-busyloop.md` |
| testcase | `phase1-testcase-failure.md` |
| health_check_failed | `phase1-health_check_failed.md` |
| simulation | `phase1-simulation.md` |

公共约束、GDB字段/skip闭集、Phase 2–5均来自base；入口只补充现场取证特点，不覆盖公共因果/交付门禁。真实入口不可单独作为完整prompt使用。`simulation` 是显式流程冒烟豁免，不做真实分析，不计入修复成功统计；仿真产品上的真实crash不等于 `exception_type=simulation`。

## 因果与交付门禁

1. **Phase 1 取证**：现场与直接机制；GDB取证完成不等于根因正确，真实失败仍可进入Phase 5报告未完成。
2. **Phase 2 充分性**：契约、状态形成/生命周期/时序、跨层依赖、候选与反证；不按固定跳数停止。unknown可继续调查或报告停止。
3. **Phase 3 设计与验证**：编辑前分类原因修复/容错加固/临时规避、反事实审查、修前契约验收；七项静态检查与运行证据分开。`not_run`只能支持有明确限制的候选，`fail`或破坏契约不能伪装安全修复交付。
4. **Phase 4 产物**：通过候选门禁才提交/导出，不意味着事故解决；产品策略不明停止提交、报告需人工决策，不必交互等待。
5. **Phase 5 报告**：Markdown分开记录mechanism/root/patch/verification/incident/unresolved/next evidence；无候选也必须报告。

## 兼容边界

- 不新增结果JSON字段或顶层status枚举；仍用 `patch_generated` / `failed_to_fix`。前者只表示候选产物，后者可表示证据、权限、源码、策略或验证条件等导致无候选。
- `patch`保持既有仓库对象结构；无patch统一 `[]`。导出URL、owners及既有元数据处理沿用base，不自造值。
- 新因果/验证语义只写 `analysis_report.md`；不要把Markdown中的pass/fail/unknown/not_run当成JSON新增枚举。
- 本仓库没有引擎schema或运行harness；静态检查不能证明消费方兼容、模型行为稳定或修复有效。部署时仍需宿主集成验证，不能把 `patch_generated` 当成功率。

## 维护验证

仅需Python 3标准库，在仓库根运行：

```sh
python3 checks/check_prompts.py
python3 checks/check_prompts.py --self-test
git diff --check
```

`checks/check_prompts.py` 检查五种装配入口、公共门禁、旧冲突pattern、结果JSON示例与八个评审场景的存在；`--self-test` 用内存突变确认关键检查能拒绝回归。不执行prompt中的命令、不联网、不写调试/回调产物。

`checks/causal-review-fixtures.md` 是八个抽象通用场景与人工判分标准。改动提示词后按该文件逐项审阅组装后的prompt；如有隔离的模型评测环境，可提供场景并检查其输出证据与门禁选择。静态通过不等于八场景模型实测通过。

这两个检查文件仅用于维护，不是新增prompt模块，也不依赖harness加载额外文件。
