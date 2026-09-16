# 接口总览

| 操作 | 端点 | job_type |
| --- | --- | --- |
| 生成 Dockerfile | `POST /v1/dockerfile-jobs` | `DOCKERFILE_GENERATION` |
| 全量检测 | `POST /v1/full-check-jobs` | `FULL_CHECK` |
| 增量检测 | `POST /v1/incremental-check-jobs` | `INCREMENTAL_CHECK` |
| 修复 MD | `POST /v1/repair-jobs` | `REPAIR` |
| 查询任务 | `GET /v1/jobs/{job_id}` | - |

创建请求含 `schema_version`、`trace_id`、`job_type` 和专有 `input`。成功受理返回 `202`、服务端生成的 `job_id` 与 `QUEUED` 状态。接口 Schema 以 `contracts/common/` 为准。

可直接交接的 JSON 请求与终态响应样例位于 `contracts/interface-index.json` 所列的四个服务目录；Markdown 文件只保留设计说明。
