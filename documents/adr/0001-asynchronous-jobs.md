# ADR-001：统一异步 Job 与错误语义

- 日期：2026-09-20
- 状态：已有契约的设计记录，待配对组确认
- 依据：E2 PPT 第 6—9、13、19、27 页；现有 task/job/error Schema

## Context

环境生成、依赖分析和修复可能超过 HTTP 请求生命周期。四个服务需要统一受理、查询和追踪方式，同时区分工具执行失败与正常分析发现。

## Decision

四类任务使用 DRAFT、FULL_CHECK、INCREMENTAL_CHECK、REPAIR，共享 schema_version、job_id、trace_id、job_type、status、execution、input、output、error。公共定义由 task.schema.json 提供，其余 Schema 通过引用复用。

四个创建端点保持不变。请求不携带 job_id；服务端受理后返回 HTTP 202 与 job_id、QUEUED。GET /v1/jobs/{job_id} 返回完整 Job 和产物引用。一次业务链沿用 trace_id，每次任务使用独立 job_id。

正常状态为 QUEUED → RUNNING → SUCCEEDED，其他终态为 FAILED、TIMED_OUT、CANCELLED。终态不可再次变化，终态必须有 finished_at。SUCCEEDED 的 error 为 null；FAILED/TIMED_OUT 必须有错误码。

MISSING、REDUNDANT 是分析发现，写入 findings 或 ERROR_REPORT。MDFixer 完成候选评估但全部拒绝时可 SUCCEEDED、accepted=false，并保留拒绝原因。

请求可携带 Idempotency-Key。实现时在同一创建端点、同一调用方范围内保存键与规范化请求体及 job_id 的关联：同键同内容返回原 job_id，同键不同内容返回 HTTP 409、REQ_1001。关联至少保留至对应 Job 被清理。此行为是实施约定，当前没有 HTTP 实现。

受理前可判定的结构错误返回 HTTP 400，使用 error.schema.json 结构，不创建 Job。受理后执行失败写入 Job.error。具体产物错误映射见产物读取约定。

## Alternatives

- 同步等待：开发简单，但长任务易触发超时，重试容易重复执行。
- 每个服务独立状态模型：局部灵活，但调用方需要维护四套处理逻辑。
- 回调推送：减少轮询，但需要额外回调地址与重试机制，E2 暂不采用。

## Consequences

调用方需保存 job_id 并轮询；后续需实现任务存储、后台执行和幂等关联。202 表示受理，不表示任务成功。轮询频率与存储清理策略在部署阶段配置。

## Validation

现有 scripts/validate.py 覆盖四类请求/响应、非法类型、部分终态规则与 MD 不等于执行失败。幂等行为、状态迁移和 HTTP 响应需后续集成验证，不能从 JSON 样例通过推断已实现。
