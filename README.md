# DevOps Build Toolchain

本仓库用于设计一条由四个服务组成的构建依赖工具链：DRAFT 生成可构建环境，BuildChecker 执行全量依赖检测，EChecker 完成跨提交增量检测，MDFixer 修复缺失依赖。

## 范围

仓库目前只包含接口契约、可交换的 JSON 样例与接口校验，不包含服务实现与实验代码。`services/`、`shared/`、`tests/`、`fixtures/` 和 `experiments/` 仍为预留目录。

四类异步任务：

- `DRAFT`
- `FULL_CHECK`
- `INCREMENTAL_CHECK`
- `REPAIR`

接口采用统一异步 Job 模型：`POST` 立即返回 `202` 与 `QUEUED`，`GET /v1/jobs/{job_id}` 查询状态与产物引用；Dockerfile、镜像、日志、依赖图、错误报告与 Patch 都通过 `artifact://` 引用交接。

## 仓库入口

- [接口设计说明](documents/interfaces/interface-overview.md)
- [JSON 接口索引](contracts/interface-index.json)
- [统一任务模型](contracts/common/task.schema.json)：`job_type`、`status`、错误码与四类任务输入输出的唯一来源
- [字段迁移说明](MIGRATION.md)
- [协作规范](CONTRIBUTING.md)

接口 Schema 在 `contracts/common/`：`task`、`job`、`artifact`、`finding`、`dependency-graph`、`error`；四类任务的请求与响应样例在 `contracts/{draft,buildchecker,echecker,mdfixer}/`；必须被拒绝的非法输入在 `contracts/negative/`。

## 校验

在仓库根目录执行：

```bash
python scripts/validate.py
```

脚本仅用 Python 标准库，会用最小的 JSON Schema 子集解释器**真实加载** `contracts/common/*.schema.json`，再叠加 Schema 表达不了的语义断言（`baseline.commit == base_commit`、错误报告的提交与配置一致性、终态规则、构建与重检的成功语义、artifact 的生产任务与提交一致性等），并用变异用例自检校验器本身。当前结果：`17 passed, 0 failed`。

样例中的仓库地址、镜像与 artifact URI 均为占位值，只用于证明结构可交换；接入真实产物后再冻结真实基线并补齐 SHA-256。
