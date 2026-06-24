## [Phase 1/5] 根因分析 — UI / 图形显示异常

**不使用 GDB/coredump**。强制按以下链路：栈分诊 → 经验路由(Gate-1) → `ui-bugfix` 或 `quickapp-bug-fix` 的 Step 1-6。
输入是 `jira_id` / `screenshot_path` / `ux_source` / `component`，不是 elf/coredump。

---

### 1. 取 issue + 栈分诊（Step 1.2，先做）

1. 有 `jira_id` → 按 ui-bugfix `routing.md §二` 双域名分流取 issue（VELAPLATFO-*→jira.n.xiaomi.com；MIWEARRTOS-*→jira-phone.mioffice.cn），下载截图/附件。
2. **栈分诊**（决定进哪个 sibling skill，错则 bounce）：照 `ui-bugfix/references/routing.md §一 栈分诊表`，优先级 Component → 包名 → 现象：
   - `component=Vela 快应用`/三方包名/`.ux`/`setStyle` → **quickapp-bug-fix**
   - `component=GUI/图形`/miwear 业务应用(home/launcher/sports/settings) → **ui-bugfix**
   - `up_assert/hardfault/KASAN/panic` → 这不是 UI bug，应走 crash 分支（exception_type 填错了）
   - **禁止在 fetch JIRA 前凭 summary 关键词定栈**；含糊先拉 component。

### 2. Gate-1 经验前置匹配（分型后立刻做）

```bash
python3 /root/.claude/experience-graphic/compile_kb.py --auto   # 路由表本地缓存,按需重编
```
- 用栈结论过滤：miwear 栈只匹配 `stack ∈ {miwear, shared}`、quickapp 栈只匹配 `{quickapp, shared}` 的卡（防跨栈误注入）。
- 把现象的可观察 tag(symptom/widget/ctx/behavior) 对照 `experience-graphic/_routing_table.yaml`：命中卡(confidence≥50%)→ 读 `units/<id>.md` 拿排查路径/判别器/negative 辅助定位；30–50% 仅参考。
- **记下注入了哪些卡**（cards_injected），Phase 4 的 Gate-2 要回填命中效果。
- 库空/无匹配则照常分析（soft-fail，不阻塞）。注：现有库多为 quickapp 栈卡，miwear 栈命中少属正常。

### 3. 按选定 skill 走 Step 1-6（根因 + 证据链）

进入 `ui-bugfix` 或 `quickapp-bug-fix` 的 SKILL.md，执行：
- **Step 1.5 版本对齐（强制前置）**：从固件版本号对齐本地仓到对应版本（corgi lgb_manifests / JIRA 评论 Gerrit link / git log --all --grep），否则极易误判 `source_missing_on_base`。
- **Step 3 分型** → **Step 4 按分型+code-map 定位代码**（禁止全仓 grep，限定子目录）→ **Step 5 完整读源码** → **Step 6 根因 + 证据链**。
- 输出标准三段供上层消费：`## 根因候选` / `## 修改点` / `## 风险与分流`。

---

### 数据源优先级（UI/graphics）

1. `jira_id` 的 description + comments（现象、复现、固件版本）
2. `screenshot_path` 截图/录屏（视觉现象）
3. Gate-1 命中卡的"排查路径 / 现象→子模式判别器"
4. `ux_source`（quickapp 栈）/ 对应栈的 code-map
5. 源码直读（按 code-map 限定子目录）

### 根因定位清单（Phase 1 完成前必须全打勾）

- [ ] 已栈分诊（miwear vs quickapp），记录判定依据（Component/包名/现象哪个命中）
- [ ] 已跑 Gate-1（compile --auto + 栈过滤路由），记录 cards_injected（可能为空）
- [ ] Step 1.5 版本对齐已通过 / 三路径全失败（后者才能报 source_missing_on_base）
- [ ] 已按分型完整读被改函数/调用链（禁止凭现象猜根因）
- [ ] **已判失真层（graphics-bug-card 核心判别）**：是否为**包装层↔LVGL 边界**(widget_*.cpp / uikit)的**双表示同步缝隙**——即包装层与 LVGL 各持一份几何/样式、跨界读/写/同步点错位；容器/渲染类现象失真层在边界**不在 LVGL 内核**（别去翻 lv_obj/lv_area）
- [ ] 已输出 `## 根因候选` / `## 修改点` / `## 风险与分流` 三段

### 🛑 修复边界（硬约束）

- 本分支**只改框架/widget/样式/资源代码**（`frameworks/runtimes/quickapp`、`frameworks/runtimes/feature`、`vendor/xiaomi/miwear/apps`、`frameworks/graphics/uikit` 等）。
- **不接受仅改三方 `.ux` 业务逻辑**（不在本仓）→ Phase 5 报 `out_of_scope: third_party_ux`。
- 根因落到 BSP/驱动/panel/crash → 类型填错，应走对应分支；Phase 5 报 `wrong_exception_type` 或 `升级到底层`。

**自动进入 Phase 2。**
