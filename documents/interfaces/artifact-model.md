# Artifact 模型

Artifact 以 URI 传递大对象：图、日志、报告与 Patch 不嵌进 Job，Job 只保存引用元数据。

## 引用结构

必需字段：`artifact_id`、`type`、`uri`、`media_type`、`producer_job_id`、`repository_commit`、`configuration_id`。

- `type` 为封闭枚举：`DOCKERFILE`、`CONTAINER_IMAGE`、`BUILD_LOG`、`DRAFT_ITERATION_LOG`、`ACTUAL_GRAPH`、`DECLARED_GRAPH`、`ERROR_REPORT`、`GIT_PATCH`、`REPAIR_REPORT`、`TEST_REPORT`。
- `uri` 允许 `artifact://`、`docker://`、`https://` 三种 scheme：产物用 `artifact://` 逻辑 URI，镜像用 `docker://` 引用。
- `sha256` 为**可选**字段，仅在需要核验内容完整性时提供；一旦提供必须是 64 位小写 hex。样例中不写占位摘要，接入真实产物后必须补真实值。

## `artifact://` 解析

```text
artifact://<namespace>/<job-id>/<file-name>
```

`artifact://` 是逻辑 URI，本仓库不提供下载服务；实际部署时由接入方约定解析规则或替换为可访问的 `https://` 地址，替换后必须同步修改契约。

## 消费方校验顺序

接收方在消费任何产物之前，按以下顺序检查：

1. `producer_job_id` 对应的任务存在且已经成功（`status` 为 `SUCCEEDED`）。
2. `repository_commit` 是 40 位完整 SHA，且与当前任务的仓库提交一致。
3. `configuration_id` 与当前任务的执行配置一致；依赖图与错误报告尤其不能跨配置复用。
4. `uri` 指向的内容可读；若提供了 `sha256`，按原始字节重新计算并比对。
5. 按 `media_type` 选择解析器；JSON 一律按 UTF-8 解析。

第 2、3 步不满足即按 `BASE_2001` / `BASE_2002` 拒绝，不启动后续任务；URI 无法读取或摘要不一致按 `REQ_1002` 拒绝。
