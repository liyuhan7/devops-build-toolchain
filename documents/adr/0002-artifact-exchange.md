# ADR-002：共享目录或离线包交换不可变产物

- 日期：2026-09-20
- 状态：提议，待配对组确认
- 依据：E2 PPT 第 5、10—12、24 页

## Context

依赖图、日志、错误报告和 Patch 不适合嵌入每次任务查询。现有 artifact:// 只有逻辑地址，未规定接收方如何读取；baseline 和 error_report 的简化引用还缺少完整生产任务信息。E2 需要明确交接规则，但无需部署下载服务。

## Decision

E2 采用共享目录或 ZIP 离线交接包；双方分别设置 ARTIFACT_ROOT。逻辑 URI 按以下规则解析：

`artifact://<namespace>/<run-key>/<relative-path>` → `<ARTIFACT_ROOT>/<namespace>/<run-key>/<relative-path>`。

namespace 标识配对组或交接空间；run-key 标识一次发布，不要求等于 job_id，以兼容现有 full001、inc001 等样例。真实生产任务以 manifest 中 producer_job_id 为准。

每次发布包含 manifest.json、jobs/ 下的生产任务快照以及文件字节。manifest 登记完整 Artifact 元数据，同时以 URI 关联不属于现有 Artifact 类型的证据文件。简化引用先通过 manifest 补全元数据，再与请求和文件内容交叉验证。

发布后同 URI 的内容不可覆盖。生产方先写临时目录、计算摘要并检查文件，再将整个目录发布；接收方只读取完整发布目录。离线 ZIP 解压到临时位置，完成检查后再放入根目录。真实跨组交接文件必须提供 SHA-256；通用 Schema 的可选字段不变，纯结构占位样例可省略。

完整结构、边界和读取顺序见 [产物读取约定](../interfaces/artifact-model.md)。未来可提供 HTTPS 下载，但保持逻辑 URI 和元数据语义；映射变化记录在交接配置中。

## Alternatives

- JSON 内嵌所有内容：直观，但会扩大响应且重复传输。
- 只传发送方绝对路径：无法跨机器使用。
- 立即部署对象存储：适合后续联调，但增加 E2 的部署负担。

## Consequences

双方无需共享同一个磁盘路径，但需要收到相同目录内容。增加 manifest 与任务快照的维护成本，换取可追溯和可复核的读取方式。镜像通过 registry 获取，不能把 docker:// 当成本地文件路径。

默认保留至本轮验收及双方依赖任务完成。发送方清理前通知消费者并记录受影响 URI，不在仍有依赖时删除。

## Validation

同一份交接包在不同 ARTIFACT_ROOT 下解析相同 URI，读取相同字节并得到相同摘要；缺失文件、摘要不一致和路径越界必须拒绝。E2 先按文档手工演练，E12 保留消费者实际读取证据。当前仓库尚无解析器或真实交接包，不声明已完成跨组读取。
