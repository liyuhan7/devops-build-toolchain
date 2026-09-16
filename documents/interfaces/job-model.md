# Job 模型

公共字段为 `schema_version`、`job_id`、`trace_id`、`job_type`、`status`、`input`、`output`、`error`、`created_at`、`started_at`、`finished_at`。

状态流转：`QUEUED -> RUNNING -> SUCCEEDED`；`QUEUED/RUNNING -> FAILED` 或 `TIMED_OUT`；未开始的任务可变为 `CANCELLED`。`SUCCEEDED` 的 `output.findings` 可以非空。
