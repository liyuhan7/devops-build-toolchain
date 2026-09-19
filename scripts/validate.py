#!/usr/bin/env python3
"""接口契约校验（仅用 Python 标准库，零第三方依赖）。

与把断言写死在脚本里的做法不同：本脚本真正加载 contracts/common/*.schema.json，
用一个最小的 JSON Schema 子集解释器执行，因此 Schema 是接口的唯一真相，脚本只补
Schema 表达不了的跨字段与状态语义。

支持的 Schema 关键字：$ref（本文件内与相对文件）、type、const、enum、required、
properties、additionalProperties、items、minLength、minimum、maximum、pattern、
format(date-time)、allOf、anyOf、oneOf、if/then/else。

覆盖的检查：
  01 四类任务的请求与响应都能通过对应 Schema
  02 非法 job_type 必须被拒绝
  03 增量任务缺少 baseline 必须被拒绝
  04 报告 MISSING 的任务必须 SUCCEEDED 且 error 为 null（发现不等于工具执行失败）
  05 Schema 管不到的语义规则，以及校验器自身的可靠性（变异用例自检）

用法：
    python scripts/validate.py [--all]
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
COMMON = CONTRACTS / "common"
INDEX_PATH = CONTRACTS / "interface-index.json"

_SCHEMA_CACHE = {}
DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")


# --------------------------------------------------------------------------
# 最小 JSON Schema 子集解释器
# --------------------------------------------------------------------------

class SchemaError(Exception):
    pass


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_schema(path):
    path = Path(path).resolve()
    if path not in _SCHEMA_CACHE:
        _SCHEMA_CACHE[path] = load_json(path)
    return _SCHEMA_CACHE[path]


def _pointer(root, pointer):
    if pointer in ("", "/"):
        return root
    node = root
    for raw in pointer.lstrip("/").split("/"):
        part = raw.replace("~1", "/").replace("~0", "~")
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def deref(node, root, base):
    """把 {"$ref": "..."} 解析成具体子 Schema；支持 #/pointer 与 file.json#/pointer。"""
    hops = 0
    while isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"]
        file_part, _, pointer = ref.partition("#")
        if file_part:
            base = (base.parent / file_part).resolve()
            root = load_schema(base)
        node = _pointer(root, pointer)
        hops += 1
        if hops > 32:
            raise SchemaError("疑似循环 $ref：%s" % ref)
    return node, root, base


def _is_type(instance, name):
    if name == "object":
        return isinstance(instance, dict)
    if name == "array":
        return isinstance(instance, list)
    if name == "string":
        return isinstance(instance, str)
    if name == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if name == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if name == "boolean":
        return isinstance(instance, bool)
    if name == "null":
        return instance is None
    return True


def validate(instance, schema, root, base, path="$", errors=None):
    """返回错误列表；空列表表示通过。"""
    if errors is None:
        errors = []
    schema, root, base = deref(schema, root, base)
    if schema is True or schema == {}:
        return errors
    if schema is False:
        errors.append("%s: 被 false schema 拒绝" % path)
        return errors

    declared = schema.get("type")
    if declared is not None:
        names = declared if isinstance(declared, list) else [declared]
        if not any(_is_type(instance, n) for n in names):
            errors.append("%s: 期望 %s，实际 %s" % (path, "/".join(names), type(instance).__name__))
            return errors

    if "const" in schema and instance != schema["const"]:
        errors.append("%s: 期望常量 %r，实际 %r" % (path, schema["const"], instance))
    if "enum" in schema and instance not in schema["enum"]:
        errors.append("%s: %r 不在枚举 %s 中" % (path, instance, schema["enum"]))

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append("%s: 长度 %d 小于 minLength %d" % (path, len(instance), schema["minLength"]))
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append("%s: %r 不匹配 %s" % (path, instance, schema["pattern"]))
        if schema.get("format") == "date-time" and not DATETIME.match(instance):
            errors.append("%s: %r 不是合法 date-time" % (path, instance))

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append("%s: %r 小于 minimum %r" % (path, instance, schema["minimum"]))
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append("%s: %r 大于 maximum %r" % (path, instance, schema["maximum"]))

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append("%s: 缺少必需字段 %s" % (path, key))
        properties = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in properties:
                validate(value, properties[key], root, base, "%s.%s" % (path, key), errors)
            elif extra is False:
                errors.append("%s: 出现未声明字段 %s" % (path, key))
            elif isinstance(extra, dict):
                validate(value, extra, root, base, "%s.%s" % (path, key), errors)

    if isinstance(instance, list) and "items" in schema:
        for index, item in enumerate(instance):
            validate(item, schema["items"], root, base, "%s[%d]" % (path, index), errors)

    for sub in schema.get("allOf", []):
        validate(instance, sub, root, base, path, errors)

    if "anyOf" in schema:
        if not any(not validate(instance, sub, root, base, path, []) for sub in schema["anyOf"]):
            errors.append("%s: anyOf 的所有分支都不匹配" % path)

    if "oneOf" in schema:
        hits = sum(1 for sub in schema["oneOf"] if not validate(instance, sub, root, base, path, []))
        if hits != 1:
            errors.append("%s: oneOf 匹配了 %d 个分支（要求恰好 1 个）" % (path, hits))

    if "if" in schema:
        if not validate(instance, schema["if"], root, base, path, []):
            if "then" in schema:
                validate(instance, schema["then"], root, base, path, errors)
        elif "else" in schema:
            validate(instance, schema["else"], root, base, path, errors)

    return errors


def check(instance, schema_file, pointer=""):
    """按 common/<schema_file>（可带 #/pointer）校验 instance，返回错误列表。"""
    path = COMMON / schema_file
    root = load_schema(path)
    node = _pointer(root, pointer) if pointer else root
    return validate(instance, node, root, path, "$")


# --------------------------------------------------------------------------
# 样例收集与遍历
# --------------------------------------------------------------------------

def load_sample(relative_path):
    return load_json(CONTRACTS / relative_path)


def walk_artifacts(value, path="$"):
    """递归找出所有 artifact 引用对象。"""
    if isinstance(value, dict):
        if "artifact_id" in value and "producer_job_id" in value:
            yield path, value
        for key, child in value.items():
            yield from walk_artifacts(child, "%s.%s" % (path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_artifacts(child, "%s[%d]" % (path, index))


def walk_findings(value, path="$"):
    """递归找出所有 finding 对象（以 finding_id + detector 识别）。"""
    if isinstance(value, dict):
        if "finding_id" in value and "detector" in value:
            yield path, value
        for key, child in value.items():
            yield from walk_findings(child, "%s.%s" % (path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_findings(child, "%s[%d]" % (path, index))


def fail(message):
    raise AssertionError(message)


def semantic_errors(job):
    """Schema 表达不了的跨字段与状态语义；返回违规说明列表（空表示通过）。

    这些不是"样例恰好一致"，而是可被本函数独立判定的规则，因此可以被变异用例检验。
    """
    errors = []
    job_type = job.get("job_type")
    status = job.get("status")
    payload = job.get("input") or {}
    output = job.get("output") or {}

    if job_type == "INCREMENTAL_CHECK":
        baseline = payload.get("baseline") or {}
        if baseline.get("commit") != payload.get("base_commit"):
            errors.append("baseline.commit 必须等于 base_commit（历史图必须能追溯到基线提交）")

    if job_type == "REPAIR":
        report = payload.get("error_report") or {}
        repository = payload.get("repository") or {}
        environment = payload.get("environment") or {}
        if report.get("repository_commit") != repository.get("commit"):
            errors.append("error_report.repository_commit 必须等于 repository.commit")
        if report.get("configuration_id") != environment.get("configuration_id"):
            errors.append("error_report.configuration_id 必须等于 environment.configuration_id")

    if status is not None:
        if status in {"SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELLED"} and not (job.get("execution") or {}).get(
            "finished_at"
        ):
            errors.append("%s 是终态，必须有 execution.finished_at" % status)
        if status == "SUCCEEDED" and job.get("error") is not None:
            errors.append("SUCCEEDED 不得带 error（MD/RD 属 findings，不是工具执行失败）")
        if status in {"FAILED", "TIMED_OUT"} and not (job.get("error") or {}).get("code"):
            errors.append("%s 必须给出 error.code" % status)

    if job_type == "DRAFT" and status == "SUCCEEDED":
        if not output.get("iterations"):
            errors.append("DRAFT：输出必须包含逐轮迭代日志")
        for key in ("build_result", "verify_result"):
            result = output.get(key) or {}
            if result.get("success") is not True or result.get("exit_code") != 0:
                errors.append("DRAFT：%s 未通过却标记 SUCCEEDED" % key)
        for index, item in enumerate(output.get("iterations") or []):
            if not item.get("change") or not item.get("reason"):
                errors.append("DRAFT：第 %d 轮缺少 change 或 reason" % (index + 1))

    if job_type == "REPAIR" and status == "SUCCEEDED":
        if output.get("accepted") is True:
            recheck = output.get("recheck_result") or {}
            if recheck.get("success") is not True or recheck.get("remaining_missing") != 0:
                errors.append("MDFixer：重检未清零却接受补丁")
            if "patch" not in output:
                errors.append("MDFixer：接受补丁必须给出 Git Patch 引用")
        else:
            candidates = output.get("rejected_candidates") or []
            if not candidates:
                errors.append("MDFixer：未接受补丁必须记录被拒候选")
            for index, candidate in enumerate(candidates):
                if not candidate.get("reason"):
                    errors.append("MDFixer：第 %d 个被拒候选缺少原因" % (index + 1))

    return errors


def mutate(job, change):
    clone = json.loads(json.dumps(job))
    change(clone)
    return clone


# --------------------------------------------------------------------------
# 测试
# --------------------------------------------------------------------------

def main():
    index = load_json(INDEX_PATH)
    entries = [item for item in index["interfaces"] if "job_type" in item]
    requests = {item["job_type"]: item["request"] for item in entries}
    responses = {item["job_type"]: item["response"] for item in entries}
    tests = []

    # 01 四类任务的请求与响应
    def all_json_parse():
        parsed = 0
        for path in CONTRACTS.rglob("*.json"):
            load_json(path)
            parsed += 1
        assert parsed >= 15, "contracts 下 JSON 数量异常：%d" % parsed

    tests.append(("全部契约 JSON 可解析", all_json_parse))

    def requests_pass():
        for job_type, relative in requests.items():
            errors = check(load_sample(relative), "task.schema.json", "/$defs/request")
            assert not errors, "%s 请求应通过：%s" % (job_type, errors[:3])

    tests.append(("四类请求通过 task.schema.json", requests_pass))

    def responses_pass():
        for job_type, relative in responses.items():
            errors = check(load_sample(relative), "task.schema.json", "/$defs/response")
            assert not errors, "%s 响应应通过：%s" % (job_type, errors[:3])

    tests.append(("四类响应通过 task.schema.json（含 Job 公共字段）", responses_pass))

    def failures_pass():
        for item in entries:
            if "failure" not in item:
                continue
            errors = check(load_sample(item["failure"]), "task.schema.json", "/$defs/response")
            assert not errors, "%s 失败样例应通过：%s" % (item["job_type"], errors[:3])

    tests.append(("失败样例（FAILED + error.code）通过 Schema", failures_pass))

    # 02 / 03 非法输入必须被拒绝
    negatives = index["negative_samples"]

    def explicit_rejections():
        job_type_errors = check(load_sample("negative/invalid-job-type.json"), "task.schema.json", "/$defs/request")
        assert job_type_errors, "job_type=ABC 必须被拒绝"
        baseline_errors = check(
            load_sample("negative/incremental-check-missing-baseline.json"), "task.schema.json", "/$defs/request"
        )
        assert baseline_errors, "增量任务缺 baseline 必须被拒绝"

    tests.append(("非法 job_type 与缺 baseline 被拒绝", explicit_rejections))

    def all_negatives_rejected():
        for item in negatives:
            errors = check(load_sample(item["path"]), "task.schema.json", "/$defs/request")
            assert errors, "%s 应被拒绝，但通过了" % item["path"]

    tests.append(("negative/ 目录内每个样例都被拒绝", all_negatives_rejected))

    # 04 MD 是成功发现，不是工具执行失败
    def md_is_not_error():
        report = load_sample("buildchecker/full-check.finding-report.json")
        errors = check(report, "finding.schema.json", "/$defs/report")
        assert not errors, "MD 报告应通过 finding.schema.json#/$defs/report：%s" % errors[:3]
        assert report["findings"], "MD 报告必须至少有一条 finding"
        for finding in report["findings"]:
            assert finding["type"] in {"MISSING", "REDUNDANT"}
        response = load_sample(responses["FULL_CHECK"])
        assert response["status"] == "SUCCEEDED" and response["error"] is None, (
            "报告 MISSING 的任务必须 SUCCEEDED 且 error 为 null"
        )
        assert response["output"]["summary"]["missing"] == len(response["output"]["findings"])

    tests.append(("MD 是成功发现：SUCCEEDED 响应 error 为 null", md_is_not_error))

    # 终态与成功语义
    def terminal_rules():
        for job_type, relative in responses.items():
            job = load_sample(relative)
            assert semantic_errors(job) == [], "%s 违反状态语义：%s" % (job_type, semantic_errors(job))
        draft = load_sample(responses["DRAFT"])
        failed = load_sample("draft/dockerfile-generation.failed.json")
        assert semantic_errors(failed) == [], "失败样例违反状态语义：%s" % semantic_errors(failed)
        succeeded_with_error = mutate(draft, lambda job: job.update({"error": {"code": "ENV_3002", "message": "x"}}))
        assert semantic_errors(succeeded_with_error), "语义层必须捕获 SUCCEEDED 却带 error"
        failed_without_code = mutate(failed, lambda job: job.update({"error": {"message": "x"}}))
        assert semantic_errors(failed_without_code), "语义层必须捕获 FAILED 却缺 error.code"
        running_without_finish = mutate(
            draft, lambda job: job.update({"status": "RUNNING", "output": None, "execution": {"created_at": "2026-09-16T10:00:00Z", "started_at": "2026-09-16T10:00:03Z", "finished_at": None}})
        )
        assert semantic_errors(running_without_finish) == [], "RUNNING 不是终态，不应要求 finished_at"
        terminal_without_finish = mutate(draft, lambda job: job["execution"].update({"finished_at": None}))
        assert semantic_errors(terminal_without_finish), "语义层必须捕获终态缺 finished_at"

    tests.append(("状态语义：终态有 finished_at，SUCCEEDED 无 error，FAILED 有 error.code", terminal_rules))

    def success_semantics():
        for job_type, relative in responses.items():
            job = load_sample(relative)
            assert semantic_errors(job) == [], "%s 样例违反成功语义：%s" % (job_type, semantic_errors(job))
        draft = load_sample(responses["DRAFT"])
        broken_build = mutate(draft, lambda job: job["output"]["build_result"].update({"success": False, "exit_code": 1}))
        assert semantic_errors(broken_build), "语义层必须捕获 DRAFT 构建失败仍标记 SUCCEEDED"
        no_reason = mutate(draft, lambda job: job["output"]["iterations"][0].update({"reason": ""}))
        assert semantic_errors(no_reason), "语义层必须捕获迭代缺少选择理由"
        repair = load_sample(responses["REPAIR"])
        not_clean = mutate(repair, lambda job: job["output"]["recheck_result"].update({"success": False, "remaining_missing": 1}))
        assert semantic_errors(not_clean), "语义层必须捕获重检未清零却接受补丁"
        no_patch = mutate(repair, lambda job: job["output"].pop("patch"))
        assert semantic_errors(no_patch), "语义层必须捕获接受补丁但无 Patch 引用"

    tests.append(("成功语义：DRAFT 构建/验证/迭代理由、MDFixer 重检清零与 Patch", success_semantics))

    def rejected_candidates_explained():
        rejected = load_sample("mdfixer/repair.rejected.json")
        out = rejected["output"]
        assert out["accepted"] is False
        assert out["rejected_candidates"], "拒绝候选必须逐条记录"
        for candidate in out["rejected_candidates"]:
            assert candidate["reason"], "每个被拒候选必须写明原因"
            assert candidate["stage"] in {"apply", "build", "test", "recheck"}
        assert rejected["status"] == "SUCCEEDED" and rejected["error"] is None, (
            "候选全部被拒是正常分析结果，任务仍为 SUCCEEDED 且 error 为 null"
        )

    tests.append(("MDFixer：被拒候选逐条记录原因，任务仍为 SUCCEEDED", rejected_candidates_explained))

    # 产物引用
    def artifact_refs():
        found = 0
        for job_type, relative in responses.items():
            job = load_sample(relative)
            repository_commit = job["input"]["repository"]["commit"]
            for path, item in walk_artifacts(job.get("output") or {}):
                found += 1
                errors = check(item, "artifact.schema.json")
                assert not errors, "%s %s 不满足 artifact.schema.json：%s" % (job_type, path, errors[:3])
                assert item["producer_job_id"] == job["job_id"], "%s %s 的生产任务应为 %s" % (job_type, path, job["job_id"])
                assert item["repository_commit"] == repository_commit, "%s %s 的 repository_commit 与任务不一致" % (job_type, path)
        assert found >= 8, "样例中的 artifact 引用过少：%d" % found

    tests.append(("artifact 引用满足 artifact.schema.json，且 producer/commit 与任务一致", artifact_refs))

    def finding_refs():
        found = 0
        for job_type, relative in responses.items():
            job = load_sample(relative)
            repository_commit = job["input"]["repository"]["commit"]
            for path, item in walk_findings(job.get("output") or {}):
                found += 1
                errors = check(item, "finding.schema.json")
                assert not errors, "%s %s 不满足 finding.schema.json：%s" % (job_type, path, errors[:3])
                assert item["repository_commit"] == repository_commit, "%s %s 的 commit 与任务不一致" % (job_type, path)
                assert item["evidence"]["artifact_uri"].startswith(("artifact://", "https://")), (
                    "%s %s 必须给出证据文件 URI" % (job_type, path)
                )
        assert found >= 2, "样例中的 finding 过少：%d" % found

    tests.append(("finding 满足 finding.schema.json，且 commit 与任务一致", finding_refs))

    def cross_field_semantics():
        for job_type, relative in responses.items():
            job = load_sample(relative)
            assert semantic_errors(job) == [], "%s 样例违反跨字段约束：%s" % (job_type, semantic_errors(job))
        incremental = load_sample(responses["INCREMENTAL_CHECK"])
        drifted = mutate(incremental, lambda job: job["input"]["baseline"].update({"commit": "1" * 40}))
        assert semantic_errors(drifted), "语义层必须捕获 baseline.commit 与 base_commit 不一致"
        assert check(drifted, "task.schema.json", "/$defs/response") == [], (
            "该约束不在 Schema 层，若 Schema 已能捕获则应从语义层移除"
        )
        repair = load_sample(responses["REPAIR"])
        wrong_commit = mutate(repair, lambda job: job["input"]["error_report"].update({"repository_commit": "2" * 40}))
        assert semantic_errors(wrong_commit), "语义层必须捕获错误报告提交与仓库提交不一致"
        wrong_config = mutate(repair, lambda job: job["input"]["error_report"].update({"configuration_id": "clang-default"}))
        assert semantic_errors(wrong_config), "语义层必须捕获错误报告配置与执行环境不一致"

    tests.append(("跨字段语义：baseline/base_commit、错误报告 commit 与 configuration 一致", cross_field_semantics))

    def validator_self_test():
        """自检：证明校验器不是空壳——篡改后必须被拒绝。"""
        draft = load_sample(responses["DRAFT"])
        assert check(draft, "task.schema.json", "/$defs/response") == [], "原始 DRAFT 响应必须通过"
        cases = [
            ("artifact 缺 configuration_id", lambda job: job["output"]["dockerfile"].pop("configuration_id")),
            ("artifact 缺 producer_job_id", lambda job: job["output"]["image"].pop("producer_job_id")),
            ("artifact URI scheme 非法", lambda job: job["output"]["image"].update({"uri": "ftp://example/x"})),
            ("artifact 类型不在枚举内", lambda job: job["output"]["image"].update({"type": "IMAGE"})),
            ("未声明的顶层字段", lambda job: job.update({"unexpected": 1})),
            ("status 取值非法", lambda job: job.update({"status": "PENDING"})),
            ("execution 缺 finished_at", lambda job: job["execution"].pop("finished_at")),
            ("缺 Job 公共字段 output", lambda job: job.pop("output")),
        ]
        for label, change in cases:
            errors = check(mutate(draft, change), "task.schema.json", "/$defs/response")
            assert errors, "校验器自检失败：%s 竟然通过了" % label

        # 语义层的自检：Schema 管不到，但语义规则必须捕获
        semantic_cases = [
            ("构建失败却标记 SUCCEEDED", lambda job: job["output"]["build_result"].update({"success": False, "exit_code": 1})),
            ("SUCCEEDED 却带 error", lambda job: job.update({"error": {"code": "ENV_3002", "message": "x"}})),
            ("终态缺 finished_at", lambda job: job["execution"].update({"finished_at": None})),
        ]
        for label, change in semantic_cases:
            assert semantic_errors(mutate(draft, change)), "语义自检失败：%s 竟然通过了" % label
        assert check(draft, "task.schema.json", "/$defs/response") == [], "自检不应污染原始样例"

    tests.append(("校验器自检：篡改后的样例必须被拒绝", validator_self_test))

    # 索引与样例齐备
    def index_files_exist():
        for item in entries:
            for key in ("request", "response"):
                path = CONTRACTS / item[key]
                assert path.is_file(), "interface-index 引用的 %s 不存在" % item[key]
            if "failure" in item:
                assert (CONTRACTS / item["failure"]).is_file(), "interface-index 引用的 %s 不存在" % item["failure"]
        for name in index["artifact_samples"]:
            assert (CONTRACTS / name).is_file(), "interface-index 引用的 %s 不存在" % name
        for item in negatives:
            assert (CONTRACTS / item["path"]).is_file(), "interface-index 引用的 %s 不存在" % item["path"]
        for name in index["schemas"].values():
            assert (CONTRACTS / name).is_file(), "interface-index 引用的 %s 不存在" % name

    tests.append(("interface-index.json 引用的文件都存在", index_files_exist))

    def coverage():
        job_types = set(requests) & set(responses)
        assert job_types == {"DRAFT", "FULL_CHECK", "INCREMENTAL_CHECK", "REPAIR"}, "四类任务样例不齐：%s" % job_types
        for job_type in job_types:
            request = load_sample(requests[job_type])
            response = load_sample(responses[job_type])
            assert request["job_type"] == response["job_type"] == job_type
            assert "job_id" not in request, "创建请求不应由客户端提供 job_id"
            assert response["job_id"], "响应必须由服务端给出 job_id"

    tests.append(("四类任务都有请求与响应样例，且请求不含 job_id", coverage))

    def enums_shared():
        task = load_schema(COMMON / "task.schema.json")
        job = load_schema(COMMON / "job.schema.json")
        enum_paths = [
            ("job_type", "/$defs/job_type"),
            ("status", "/$defs/status"),
            ("execution", "/$defs/execution"),
        ]
        for name, pointer in enum_paths:
            from_task = _pointer(task, pointer)
            from_job_ref = job["properties"][name]["$ref"]
            file_part, _, ref_pointer = from_job_ref.partition("#")
            assert file_part == "task.schema.json", "job.schema.json 的 %s 必须复用 task.schema.json" % name
            assert _pointer(task, ref_pointer) == from_task, "%s 的定义在 job 与 task 之间不一致" % name
        error_codes = set(_pointer(task, "/$defs/status")["enum"])
        assert "QUEUED" in error_codes and "CANCELLED" in error_codes

    tests.append(("枚举唯一来源：job.schema.json 复用 task.schema.json 的定义", enums_shared))

    verbosity = "--all" in sys.argv
    passed = 0
    for label, test in tests:
        try:
            test()
            passed += 1
            print("[PASS] %s" % label)
        except Exception as error:  # noqa: BLE001 - 校验脚本需要收集所有失败
            print("[FAIL] %s: %s" % (label, error))
            if verbosity:
                import traceback

                traceback.print_exc()
    failed = len(tests) - passed
    print("%d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
