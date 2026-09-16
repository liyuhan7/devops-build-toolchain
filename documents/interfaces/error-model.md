# 错误模型

系统错误写入 `job.error`，其中包含 `code`、`message` 和可选 `details_uri`。推荐错误码：`REQ_1001`、`REQ_1002`、`BASE_2001`、`BASE_2002`、`BASE_2003`、`ENV_3002`、`EXEC_4002`、`ANALYSIS_5001`、`REPAIR_6001`。

MD/RD 不属于 `job.error`，而是 `output.findings`。
