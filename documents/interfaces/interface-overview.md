# 接口总览

| 操作 | 端点 | job_type |
| --- | --- | --- |
| 生成构建环境 | `POST /v1/dockerfile-jobs` | `DRAFT` |
| 全量检测 | `POST /v1/full-check-jobs` | `FULL_CHECK` |
| 增量检测 | `POST /v1/incremental-check-jobs` | `INCREMENTAL_CHECK` |
| 修复缺失依赖 | `POST /v1/repair-jobs` | `REPAIR` |
| 查询任务 | `GET /v1/jobs/{job_id}` | - |

## 提交与查询

创建请求含 `schema_version`、`trace_id`、`job_type` 和专有 `input`，可携带 `Idempotency-Key` 请求头以保证重试幂等。成功受理返回 `202` 与 `{ "job_id": "...", "status": "QUEUED" }`。查询 `GET /v1/jobs/{job_id}` 返回公共字段、状态与产物引用。

本仓库只定义接口契约，不包含 HTTP 服务实现。

## Schema

接口 Schema 以 `contracts/common/` 为准：

| 文件 | 作用 |
| --- | --- |
| `task.schema.json` | 统一任务模型：`job_type`、`status`、错误码、`execution` 与四类任务输入输出的**唯一来源** |
| `job.schema.json` | Job 公共字段，用于查询响应；枚举通过 `$ref` 复用 `task.schema.json` |
| `artifact.schema.json` | 产物引用：URI、媒体类型、仓库提交、执行配置、生产任务 |
| `finding.schema.json` | 一条 finding（根对象）与完整报告（`#/$defs/report`） |
| `dependency-graph.schema.json` | 实际/声明依赖图 |
| `error.schema.json` | `job.error` 的结构与错误码 |

## 样例

可直接交接的 JSON 样例见 `contracts/interface-index.json`，覆盖四类任务的请求与响应、失败终态、被拒候选，以及 `contracts/negative/` 下必须被拒绝的非法输入。Markdown 文件只保留设计说明。

样例中的仓库地址、镜像与 artifact URI 均为占位值，只用于证明结构可交换；接入真实产物后再冻结真实基线与 SHA-256。

## 校验

```bash
python scripts/validate.py
```

脚本真实加载 `contracts/common/*.schema.json` 并叠加跨字段语义断言，同时用变异用例自检校验器本身。

## 设计决策与产物读取

- [ADR 索引](../adr/README.md)：决策背景、替代方案、代价和实现差距。
- [产物读取约定](artifact-model.md)：共享目录/离线包、URI 映射、manifest、基线校验和错误处理。

新增读取协议尚待配对组确认，仓库当前没有产物解析器或下载服务。
