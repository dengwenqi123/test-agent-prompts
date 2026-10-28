"""Check prompt data only; never execute embedded commands or contact services."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = "base.agent.md"
ENTRIES = [f"phase1-{name}.md" for name in (
    "crash", "busyloop", "testcase-failure", "health_check_failed", "simulation"
)]
BANNED = (
    "ps_output_present", "仅两类合法例外", "唯一可 `patch=[]` 的例外",
    "两处冲突时以本节为准", "不再进 Step 2", "不再继续 Step 2",
    "跳过 Step 2", "失败则 `null`", "✅ AI 自检通过",
    "禁止写 `analysis_report.md`", "自检格式化走过场",
    "Log 模式仅用于补充 GDB 看不到的跨核时间线",
)
TOP_KEYS = {"debug_session_id", "status", "patch", "diagnosis", "metrics"}
PATCH_KEYS = set("repo branch commit patch_urls patch_filenames patch_sha256s "
                 "patch_size_bytes commits_count export_status files_changed owners".split())
PATCH_ALLOWED = PATCH_KEYS | {"owners_reason", "base_remote", "base_ref", "export_error"}
GATES = ("根因充分性门禁", "3.0 修复设计", "3.3 AI 自检与验证门禁")


def check(docs, fixtures):
    errors = []

    def need(ok, message):
        if not ok:
            errors.append(message)

    base = docs[BASE]
    need(base.count("{{PHASE1}}") == 1, "base: one assembly slot required")
    for token in (*GATES, "反事实", "不按固定跳数", "not_run 不等于 fail",
                  "同一缺证据失败项禁止给修复建议或生成修复",
                  "单次不复现", "故障注入", "无需凑固定数量"):
        need(token in base, f"base: missing {token}")
    for section in ("mechanism", "root", "patch", "verification", "incident",
                    "unresolved", "next evidence"):
        need(f"## {section} —" in base, f"report: missing {section}")
    review = base.split("### 3.3", 1)[-1].split("## [Phase 4/5]", 1)[0]
    for item in ("语法", "逻辑", "类型", "资源对称", "边界条件", "副作用", "头文件"):
        need(f"| {item} |" in review, f"review: missing {item}")
    for name, text in docs.items():
        for token in BANNED:
            need(token not in text, f"{name}: legacy conflict {token}")
        need("fb" + "0" not in text.lower(), f"{name}: case-specific overfit")
    for name in ENTRIES:
        text = docs[name]
        assembled = base.replace("{{PHASE1}}", text)
        for phase in range(1, 6):
            need(assembled.count(f"## [Phase {phase}/5]") == 1,
                 f"{name}: phase {phase} assembly")
        need("{{PHASE1}}" not in assembled, f"{name}: unresolved slot")
        if "simulation" in name:
            for token in ("显式 simulation 豁免", "Phase 2 根因充分性门禁",
                          "Phase 3 修复设计", "禁止 emit", "不计入真实修复成功统计"):
                need(token in text, f"simulation: missing {token}")
        else:
            for token in ("base.agent.md", "GDB Execution Checkpoint", "合法 skip",
                          "公共 Phase 2 根因充分性门禁", "Phase 3 修复设计与验证",
                          "Phase 5", "未完成报告", "不强制产 patch"):
                need(token in text, f"{name}: missing delegation {token}")
    blocks = re.findall(r"```json\n(.*?)\n```", "\n".join(docs.values()), re.S)
    results = []
    for block in blocks:
        if '"patch"' not in block:
            continue
        try:
            result = json.loads(block)
        except ValueError:
            errors.append("invalid result JSON example")
            continue
        results.append(result)
        need(set(result) == TOP_KEYS, "result: top-level fields changed")
        need(result.get("status") in {"patch_generated", "failed_to_fix"}, "result: status")
        need(set(result.get("diagnosis", {})) == {"root_cause", "exception_type", "confidence"},
             "result: diagnosis fields changed")
        need(result.get("diagnosis", {}).get("confidence") in {"high", "medium", "low"},
             "result: confidence")
        need(set(result.get("metrics", {})) == {"debug_duration_sec", "retry_count"},
             "result: metrics fields changed")
        patches = result.get("patch")
        need(isinstance(patches, list), "result: patch must be array")
        if not isinstance(patches, list):
            continue
        need(bool(patches) == (result.get("status") == "patch_generated"),
             "result: status/patch mismatch")
        for patch in patches:
            need(isinstance(patch, dict) and PATCH_KEYS <= set(patch) <= PATCH_ALLOWED,
                 "result: patch object structure changed")
            if not isinstance(patch, dict):
                continue
            lists = [patch.get(key) for key in ("patch_urls", "patch_filenames", "patch_sha256s")]
            need(all(isinstance(value, list) for value in lists), "result: export arrays")
            if all(isinstance(value, list) for value in lists):
                need(len({len(value) for value in lists}) == 1, "result: export array lengths")
            owners = patch.get("owners")
            need(isinstance(owners, list), "result: owners must be array")
            if isinstance(owners, list):
                for owner in owners:
                    need(isinstance(owner, dict)
                         and set(owner) == {"name", "email", "affected_files"}
                         and isinstance(owner["affected_files"], list), "result: owner structure")
    need({r.get("status") for r in results} == {"patch_generated", "failed_to_fix"},
         "result: both outcome examples required")
    for number in range(1, 9):
        match = re.search(rf"## S{number} —.*?(?=\n## |\Z)", fixtures, re.S)
        need(bool(match) and all(t in match[0] for t in ("- 输入：", "- 预期：", "- 禁止：")),
             f"fixture S{number}: incomplete")
    need("fb" + "0" not in fixtures.lower(), "fixtures: case-specific overfit")
    return errors


def self_test(docs, fixtures):
    mutations = [(BASE, docs[BASE] + "\n" + token) for token in BANNED]
    for old, new in (
        ('"status": "patch_generated"', '"status": "fixed"'),
        ('"patch": []', '"patch": null'),
        ('"patch": []', '"patch": ["diff"]'),
        ('"status": "failed_to_fix",', '"status": "failed_to_fix", "incident": "resolved",'),
        ("{{PHASE1}}", ""),
        ("not_run 不等于 fail", ""),
        ("## incident —", "## outcome —"),
    ):
        mutations.append((BASE, docs[BASE].replace(old, new)))
    for name in ENTRIES[:-1]:
        mutations.append((name, docs[name].replace("公共 Phase 2 根因充分性门禁", "")))
    name = ENTRIES[-1]
    mutations.append((name, docs[name].replace("显式 simulation 豁免", "")))
    for name, text in mutations:
        changed = dict(docs, **{name: text})
        if not check(changed, fixtures):
            raise SystemExit(f"FAIL: mutation escaped detection in {name}")
    if not check(docs, fixtures.replace("## S8 —", "## omitted —")):
        raise SystemExit("FAIL: missing fixture escaped detection")
    print(f"PASS: {len(mutations) + 1} in-memory regression mutations rejected")
    block = next(b for b in re.findall(r"```json\n(.*?)\n```", docs[BASE], re.S)
                 if '"patch"' in b)
    for export_failed in (False, True):
        result = json.loads(block)
        patch = result["patch"][0]
        patch.update(owners_reason="recent_commit_authors", base_remote=None, base_ref="m/topic")
        if export_failed:
            patch.update(export_status="failed", export_error="upload unavailable",
                         patch_urls=[], patch_filenames=[], patch_sha256s=[],
                         patch_size_bytes=0, commits_count=0)
        changed = dict(docs, **{BASE: docs[BASE].replace(block, json.dumps(result))})
        if check(changed, fixtures):
            raise SystemExit("FAIL: existing optional metadata/export-failure rejected")
    print("PASS: 2 valid optional-metadata/export-failure examples accepted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    docs = {name: (ROOT / name).read_text(encoding="utf-8") for name in [BASE, *ENTRIES]}
    fixtures = (ROOT / "checks/causal-review-fixtures.md").read_text(encoding="utf-8")
    errors = check(docs, fixtures)
    if errors:
        raise SystemExit("FAIL:\n" + "\n".join(errors))
    print("PASS: 5 assemblies, common gates, result examples, 8 fixture definitions")
    if args.self_test:
        self_test(docs, fixtures)


if __name__ == "__main__":
    main()
