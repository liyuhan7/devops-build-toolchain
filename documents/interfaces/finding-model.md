# Finding 模型

Finding 表示成功分析得到的领域结论。`type` 只能为 `MISSING` 或 `REDUNDANT`，并记录 `target`、`dependency`、`repository_commit`、`configuration_id`、`detector` 与 `evidence`。

MDFixer 只接受 `MISSING`。收到 `REDUNDANT` 或其他 finding 类型时，服务返回 `REPAIR_6001`。
