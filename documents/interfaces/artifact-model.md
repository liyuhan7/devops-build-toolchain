# 产物模型与读取约定

状态：E2 可评审方案，待配对组确认。设计依据见 [ADR-002](../adr/0002-artifact-exchange.md)。本文定义协议，不表示仓库已实现解析器、下载服务或真实产物交接。

## 1. 交接方式与配置

E2 使用共享目录或 ZIP 离线包。发送方提供整个发布目录，接收方保存到本机 ARTIFACT_ROOT；两台机器的根目录可以不同。目录路径不写入 Job。真实 namespace、根目录位置、交接渠道、访问权限和清理时间由双方在 ADR 索引的确认记录中填写。

示例 URI：`artifact://pair01/full001/md-report.json`。

对应目录：

```text
<ARTIFACT_ROOT>/
  pair01/
    full001/
      manifest.json
      jobs/job-full-001.json
      md-report.json
      evidence/finding-001.json
```

pair01、full001、job-full-001 均为示例。已有 example/full001 URI 使用相同规则，无需将 run-key 改成 job_id。

## 2. URI 到文件的确定性映射

格式为 `artifact://<namespace>/<run-key>/<relative-path>`。namespace 和 run-key 仅允许字母、数字、下划线及连字符，区分大小写；relative-path 使用 / 分隔，允许子目录。

解析步骤：

1. 解析 scheme、namespace、run-key 和相对路径，拒绝用户名、密码、端口、查询参数和 fragment。
2. artifact URI 不允许百分号编码、反斜杠、空路径段、`.`、`..`、盘符和绝对路径。为兼容 Windows，每个路径段只允许 ASCII 字母、数字、下划线、连字符和点，不能以点结束，不能使用 Windows 保留设备名。
3. 将各段连接至已配置的 ARTIFACT_ROOT，解析实际路径。结果必须位于该根目录内；交接包不允许符号链接、junction 或其他重解析点，不跟随链接跨目录读取。
4. 在 `<namespace>/<run-key>/manifest.json` 中按完整 URI 查找唯一条目，再读取对应文件。不得猜测另一个文件名或默认读取最新版本。

路径映射只适用于 artifact://，不适用于 docker:// 或 https://。只信任双方约定的发布根目录及交接渠道，SHA-256 校验完整性，不证明发送者身份。

## 3. 发布清单 manifest.json

manifest 是独立交接文件，不作为 Job 新字段。协议版本为 manifest_version=1.0，必需字段如下；未列字段暂不使用，扩展需版本协商。

| 字段 | 类型与规则 |
| --- | --- |
| manifest_version | 字符串，固定 1.0 |
| namespace / run_key | 字符串，与所在目录和 URI 一致 |
| repository_url | 字符串，与生产和消费请求的仓库地址一致；别名须另行确认，不能只比 SHA |
| artifacts | 数组，每项符合 contracts/common/artifact.schema.json；本地发布至少有一项 |
| supporting_files | 数组，可为空；登记证据等辅助文件 |
| jobs | 数组，包含所有被本清单条目引用的生产任务 |

artifacts 中 URI 和 artifact_id 在该清单中唯一。真实跨组交接的文件条目必须填写按原始文件字节计算的 sha256（64 位小写十六进制）。这比通用 Schema 更严格；Schema 中 sha256 仍可选，现有占位样例不据此冒充完整交接包。

supporting_files 每项含 uri、media_type、producer_job_id、repository_commit、configuration_id、sha256，字段类型沿用 Artifact 定义。它不带 artifact_id/type，因为现有 Artifact 枚举未定义通用证据类型。URI 不得与 artifacts 重复，且同样映射到本发布目录。

jobs 每项含 job_id 和 snapshot_path 两个字符串。snapshot_path 是相对于发布目录的安全路径，如 jobs/job-full-001.json；采用第 2 节路径限制。任务快照符合 task.schema.json 的 response 定义及语义约束，job_id 必须匹配。离线快照作为受信交接包的来源记录；在线部署后可结合 GET /v1/jobs/{job_id} 复核。快照不得含凭据。

所有 artifact:// 文件条目属于当前 namespace/run-key。跨发布目录引用必须随交接提供对应目录及其清单。baseline.actual_graph_uri、error_report.uri、evidence.artifact_uri 等简化引用先从对应清单补全来源信息，缺少条目时拒绝，不凭 URI 路径推断生产任务。

## 4. 文件类型与解析方式

| 内容 | media_type | 读取方式 |
| --- | --- | --- |
| 实际/声明依赖图 | application/json | UTF-8 JSON，按 dependency-graph.schema.json 校验 |
| 错误报告 | application/json | 按 finding.schema.json#/$defs/report 校验 |
| 迭代日志、修复报告、测试报告、证据 | application/json | UTF-8 JSON；业务结构需对应生产者另行定义，当前不是全部已有 Schema |
| Dockerfile、构建文本日志 | text/plain | UTF-8 文本 |
| Git Patch | text/x-diff | 保留原始字节，应用前检查目标仓库与提交 |

先核验摘要，再解码；禁止为了计算摘要先转换换行或重新序列化 JSON。JSON 须拒绝重复键和解析错误。格式正确不代表业务结论可信，还需下一节的一致性校验。

https:// 直接按地址下载文件，再执行相同的摘要和内容校验。首次接入必须提供对应清单；跨来源重定向需重新确认访问配置，不自动转发凭据。现有 Schema 正则也接受 http://，但本读取约定只启用 artifact://、docker://、https://；将来应同步收紧 Schema，目前不能声称 Schema 已拒绝 HTTP。

docker://registry/repository@sha256:<digest> 表示容器镜像，去掉 docker:// 后由容器运行时获取，不能使用文件读取器。真实交接应固定镜像 digest 并验证；旧样例的 tag 是占位值。镜像 digest 与文件 sha256 不混用，Artifact.sha256 不用于填写镜像摘要。镜像的仓库提交和配置依然通过完整 Artifact 元数据及任务来源核对。

## 5. 消费方检查顺序

1. 检查 URI、manifest 版本、条目唯一性及文件是否存在，解析对应生产任务。
2. 业务输入（环境、图、报告、待采用补丁）要求生产任务 SUCCEEDED。日志、失败详情及拒绝候选证据允许来自 FAILED/TIMED_OUT/CANCELLED 等终态任务，仅用于诊断；未完成任务的实时日志流不属于本协议。
3. 核对仓库身份、提交和配置，规则见下表。逐条核对图或报告内部元数据，不能只相信 URI 引用外层字段。
4. 有效文件条目的 producer_job_id 必须存在于 jobs；其提交和配置与相应生产任务一致。DRAFT 输入未携带 configuration_id 时，以成功输出的环境产物元数据声明配置，相关产物需一致。
5. 计算摘要并核对；按 media_type 和相应 Schema 解析。读取报告中的 evidence URI 时再次执行相同读取流程。
6. 只在全部业务检查通过后启动后续计算；失败时记录 URI、检查阶段和错误码。

| 消费场景 | 提交与配置判据 |
| --- | --- |
| 普通当前版本图/报告/环境 | 与 input.repository.commit 和 environment.configuration_id 一致 |
| EChecker 历史图 | 图.repository_commit == baseline.commit == base_commit；允许不同于新 repository.commit；baseline 和图的 configuration_id 与当前环境一致 |
| MDFixer 输入报告 | 报告及各 finding 的提交和配置匹配当前任务；仅允许 MISSING，否则整体拒绝 |
| Patch | repository_commit 表示补丁应用前的基准提交；实际应用及构建、测试、重检另行验证 |

EChecker 当前响应没有 ERROR_REPORT 引用，需要后续补齐后才可直接交给 MDFixer；本约定不假定该链路已经实现。

## 6. 失败语义

| 情况 | 错误码 |
| --- | --- |
| URI 非法、路径越界、版本不支持、内容结构错误 | REQ_1001 |
| 非基线文件不存在/无权限、清单缺条目、摘要不一致、下载失败 | REQ_1002 |
| 仓库身份或提交不匹配 | BASE_2001 |
| 配置不匹配 | BASE_2002 |
| 历史图不存在、来源任务未成功或其他原因不可用 | BASE_2003 |
| 修复报告含非 MISSING 发现 | REPAIR_6001 |

基线读取失败使用 BASE_2003，并在 message/details_uri 说明底层读取原因；明确的提交或配置不匹配仍分别使用 BASE_2001/BASE_2002。普通业务产物来源未成功视为不可消费，使用 REQ_1002。

受理前发现问题时不创建 Job，按 error.schema.json 返回错误对象（本协议约定输入相关拒绝为 HTTP 400）；受理后发现问题时将当前 Job 标为 FAILED 并写入 job.error。上游任务保持原状态。需要后台检查才能知道的 URI 可读性问题，不要求同步 HTTP 完成检查。

## 7. 发布、接收与保留

生产方写完文件后生成摘要、清单和终态任务快照，再整体发布；同 URI 的字节和元数据不可覆盖，更新使用新的 run-key。离线包只包含该发布目录树，不包含本机绝对路径。接收方先检查归档成员，拒绝绝对路径、越界成员和链接，再解压到临时目录，验证完成后启用。

双方保留产物至本轮验收和相关下游任务结束。清理须记录涉及 URI 并通知消费者；失效 URI 不重定向到新版本。

## 8. E2 演练与后续验收

以下是待执行步骤，不是已通过的联调记录：

1. 生产方选取一份实际报告，按目录结构放置文件与证据，填写完整元数据及实际生产任务快照；人工样本使用 INSTRUCTOR_ORACLE，不冒充工具检测结果。
2. 对原始字节计算 SHA-256，登记 manifest。可用 PowerShell `Get-FileHash -Algorithm SHA256 -LiteralPath <文件路径>`；登记时将结果转为小写。
3. 将目录交给另一组，接收方使用不同 ARTIFACT_ROOT，按同一 URI 找到文件，比较摘要并校验内容。
4. 分别测试缺文件、字节被修改、配置不同、历史图提交错误和非 MD 修复报告，记录预期错误码。
5. 保存实际接收者、日期、仓库 SHA、URI、摘要、验证命令、结果与失败原因，作为后续 E12 读取证据。

`python scripts/validate.py` 目前只检查已有 JSON 契约及部分语义，不校验 manifest、读取真实文件或验证下载行为。解析器、清单 Schema、自动化读取测试和真实跨组记录属于后续实施工作。
