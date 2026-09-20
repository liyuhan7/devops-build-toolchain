# Job 模型

## 公共字段

Job 公共字段为 `schema_version`、`job_id`、`trace_id`、`job_type`、`status`、`execution`、`input`、`output`、`error`。

时间戳统一放在 `execution` 内，顶层不再出现 `created_at` 等字段：

```json
"execution": {
  "created_at": "2026-09-16T10:00:00Z",
  "started_at": "2026-09-16T10:00:03Z",
  "finished_at": "2026-09-16T10:02:17Z"
}
```

三个字段都必填：`started_at` 与 `finished_at` 在任务未开始或未结束时取 `null`。

## 请求与响应

- **创建请求**：`schema_version`、`trace_id`、`job_type`、`input`。不含 `job_id`（由服务端产生）、`status`、`execution`、`output`、`error`。
- **查询响应**：公共字段全部必备。`output` 与 `error` 允许为 `null`。

请求与响应都必须是 `task.schema.json` 中四类任务的合法对象：Schema 用 `if/then` 按 `job_type` 强制各自的专有输入，`input` 里出现未声明字段会被直接拒绝。

## 状态

`QUEUED -> RUNNING -> SUCCEEDED` 是正常路径；终态还包括 `FAILED`、`TIMED_OUT`、`CANCELLED`，终态不可再变化。

约束（由 `scripts/validate.py` 断言）：

- 终态必须有 `execution.finished_at`。
- `SUCCEEDED` 必须 `error` 为 `null`。
- `FAILED` / `TIMED_OUT` 必须给出 `error.code`。
- 检测到 `MISSING` / `REDUNDANT` 不是失败：任务仍为 `SUCCEEDED`，发现写入 `ERROR_REPORT` 的 `findings`。
- DRAFT 只有在干净构建与验证都通过、且逐轮迭代都记录了修改内容和理由时才能标记 `SUCCEEDED`。
- MDFixer 只有在构建和验证均 success=true、exit_code=0，且重检成功并不再报告 MISSING 时才能接受补丁；没有可接受候选时任务正常完成，但 `accepted` 为 `false` 且必须逐条记录被拒原因。

## 错误

`job.error` 含 `code`、`message` 和可选 `details_uri`。错误码取值见 `contracts/common/error.schema.json`：

| 错误码 | 含义 |
| --- | --- |
| `REQ_1001` | 请求缺少字段或枚举非法 |
| `REQ_1002` | 产物 URI 无法读取或摘要不一致 |
| `BASE_2001` | 提交不匹配 |
| `BASE_2002` | 配置不匹配 |
| `BASE_2003` | 基线缺失或不可用 |
| `ENV_3002` | 镜像或环境构建失败 |
| `EXEC_4002` | 任务超时 |
| `ANALYSIS_5001` | 分析器执行失败 |
| `REPAIR_6001` | 修复输入非法（例如消费了非 MISSING 的发现） |

领域发现（MISSING / REDUNDANT）不是错误，写入 `ERROR_REPORT` 的 `findings`，结构见 `contracts/common/finding.schema.json`。
