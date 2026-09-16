# DevOps Build Toolchain

本仓库用于设计一条由四个服务组成的构建依赖工具链：DRAFT 生成可构建环境，BuildChecker 执行全量依赖检测，EChecker 完成跨提交增量检测，MDFixer 修复缺失依赖。

## 当前范围

仓库目前仅包含 E2 阶段的接口设计草案，不包含服务实现、运行脚本、实验方案或实验结果。`services/`、`shared/`、`scripts/`、`tests/`、`fixtures/` 和 `experiments/` 仅预留目录。

接口采用统一异步 Job 模型，并通过 Artifact URI 传递 Dockerfile、镜像、日志、依赖图和 Patch。四类任务分别为：

- `DOCKERFILE_GENERATION`
- `FULL_CHECK`
- `INCREMENTAL_CHECK`
- `REPAIR`

## 仓库入口

- [接口设计说明](documents/interfaces/interface-overview.md)
- [JSON 接口索引](contracts/interface-index.json)
- [协作规范](CONTRIBUTING.md)
- `contracts/common/`：公共 Job、Artifact、Finding、Dependency Graph 与 Error Schema
- `contracts/{draft,buildchecker,echecker,mdfixer}/`：四类任务的 JSON 请求与响应草案

当前 JSON 仅用于配对组讨论和字段对齐，字段冻结、服务实现及实验文档将在后续阶段完成。
