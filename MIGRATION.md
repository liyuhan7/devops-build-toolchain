# 字段迁移说明

本文件记录契约命名的一次统一：早期样例与文档使用的字段名与现行契约不同。若手上的契约仍是旧命名，按下表迁移，否则校验会直接拒绝（未声明字段与缺失必填字段都会被拦截）。

## 一、命名变更

| 旧命名 | 现行命名 | 说明 |
| --- | --- | --- |
| `job_type: "DOCKERFILE_GENERATION"` | `job_type: "DRAFT"` | 四类任务统一为 `DRAFT`、`FULL_CHECK`、`INCREMENTAL_CHECK`、`REPAIR`；端点路径 `/v1/dockerfile-jobs` 不变 |
| 顶层 `created_at` / `started_at` / `finished_at` | `execution.created_at` / `execution.started_at` / `execution.finished_at` | 时间戳统一收进 `execution`；三个字段都必填，未开始或未结束时取 `null` |
| artifact 的 `commit` | artifact 的 `repository_commit` | 与 job、finding 中的字段名一致，且不会与 `baseline.commit` 混淆 |
| REPAIR 输入里表示执行环境的 `execution` | `environment` | Job 顶层的 `execution` 只放时间戳；输入里的执行环境另用 `environment`，两者不再同名 |
| `missing_dependency_report` | `error_report` | REPAIR 消费的是完整错误报告引用 |
| artifact 类型 `IMAGE` | `CONTAINER_IMAGE` | `type` 现为封闭枚举，取值见 `contracts/common/artifact.schema.json` |

## 二、结构变更

- **REPAIR 的 `error_report` 升级为完整引用**：由单字段 `{ "artifact_uri": "..." }` 改为 `{ uri, media_type, repository_commit, configuration_id, sha256? }`，前四项必填，否则无法校验基线一致性。
- **REPAIR 的构建与验证命令移入 `environment`**：`build_command`、`verify_command` 不再放在 `input` 顶层。
- **artifact 的 `configuration_id` 变为必填**：每个产物都必须能追溯到配置。
- **artifact 的 `sha256` 保持可选**：仅在需要核验内容完整性时提供；提供后必须是 64 位小写 hex。样例中不写占位摘要，接入真实产物后必须补真实值。
- **artifact 的 `uri` 放开 scheme**：允许 `artifact://`、`docker://`、`https://`；镜像用 `docker://` 引用。
- **`input` 按任务类型约束**：四类任务的专有输入字段由 Schema 强制，未声明的字段会被拒绝。
- **响应必备字段补齐**：`job_id`、`status`、`execution`、`input`、`output`、`error` 全部必填。
- **错误码表统一**：`INPUT_1001` → `REQ_1001`，`VERSION_1002` → `BASE_2001`，并补齐 `REQ_1002`、`BASE_2002`、`BASE_2003`、`REPAIR_6001`，详见 `contracts/common/error.schema.json`。

## 三、新增的样例

| 路径 | 用途 |
| --- | --- |
| `contracts/draft/dockerfile-generation.failed.json` | DRAFT 失败终态（`FAILED` + `ENV_3002` + `details_uri`） |
| `contracts/mdfixer/repair.rejected.json` | 候选全部被拒（`accepted: false` + 逐条记录失败阶段与原因），任务仍为 `SUCCEEDED` |
| `contracts/buildchecker/full-check.finding-report.json` | `ERROR_REPORT` 引用的报告内容（等待消费的 MD 报告） |
| `contracts/negative/invalid-job-type.json` | `job_type` 不属于四类，必须被拒绝 |
| `contracts/negative/incremental-check-missing-baseline.json` | 增量任务缺少 `baseline`，必须被拒绝 |

负向样例的路径与拒绝理由登记在 `contracts/interface-index.json` 的 `negative_samples`。

## 四、保持不变的约定

- 端点与方法：`POST /v1/{dockerfile-jobs,full-check-jobs,incremental-check-jobs,repair-jobs}`、`GET /v1/jobs/{job_id}`。
- 创建请求返回 `202` 与服务端生成的 `job_id`，状态以 `QUEUED` 开始；创建请求可携带 `Idempotency-Key`。
- 状态枚举与终态规则；`MISSING` / `REDUNDANT` 属 `output` 里的 findings，不是 `job.error`。
- 产物以 `artifact://` 逻辑 URI 交接，消费方按仓库提交、执行配置与（可选的）`sha256` 校验后再解析。

## 五、校验

```bash
python scripts/validate.py
```

校验器直接加载 `contracts/common/*.schema.json`，因此上表的命名与必填变化都会在样例上体现为硬失败。
