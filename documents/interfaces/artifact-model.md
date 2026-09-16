# Artifact 模型

Artifact 以 URI 传递大对象，不能将图、日志或 Patch 直接嵌入 Job。课堂原型使用 `artifact://` 逻辑 URI；实现仓库必须在 README 说明解析或下载方式。

必需字段：`artifact_id`、`type`、`uri`、`media_type`、`producer_job_id`、`repository_commit`、`configuration_id`。`sha256` 用于内容完整性核验。
