# ADR-003：基线一致性与补丁接受条件

- 日期：2026-09-20
- 状态：提议，部分规则已有校验
- 依据：E2 PPT 第 5、8—10、21—23 页

## Context

合法 JSON 不保证数据属于正确源码或构建配置。历史图必须来自旧提交；修复必须消费当前版本的 MD。只检查重检结果可能错误接受构建或测试失败的补丁。

## Decision

1. 所有提交使用完整 40 位 SHA，并核对仓库身份；仅有格式正确的占位 SHA 不能证明真实版本存在。
2. 增量检测要求 baseline.commit == base_commit，图的 repository_commit 同样等于 base_commit；这些字段不要求等于新提交 repository.commit。
3. baseline、图、当前 environment 的 configuration_id 必须一致；配置标识对应的编译器、选项、构建目标与环境定义变化时生成新标识。配置不兼容时重新全量检测。
4. REPAIR 的报告仓库、提交和配置必须匹配当前输入；每条 finding 也必须与报告一致。只接受 MISSING，含 REDUNDANT 的报告整体按 REPAIR_6001 拒绝，不静默丢弃。
5. 接受补丁要求应用成功、构建成功且 exit_code=0、验证成功且 exit_code=0、重检成功且 remaining_missing=0，并给出 Patch 引用。修复条目的 finding_id、target、dependency 必须对应输入报告。
6. 无可接受候选时 accepted=false，记录失败阶段、退出码、日志与原因；修复评估本身正常完成仍可 SUCCEEDED。
7. 业务产物来自成功生产任务；失败/超时/取消任务的日志可用于诊断，但不能当作有效基线或已验证修复结果。

## Alternatives

- 仅检查 Schema：不能表达跨对象一致性和文件内容真实性。
- 仅核对提交：同一提交在不同配置下依赖图仍可能不同。
- 仅重检清零就接受补丁：可能把破坏构建或测试的修改当成有效修复。

## Consequences

消费者需要在启动分析或修复前读取元数据和报告。配置变化可能要求重新生成基线。版本错误用 BASE_2001，配置错误用 BASE_2002，缺失或不可用基线用 BASE_2003，非 MD 修复输入用 REPAIR_6001。

## Validation 与实现差距

现有校验已检查 baseline/base_commit、增量配置一致性、修复报告提交和配置、接受补丁时构建/测试成功、重检清零及 Patch 引用。报告交接校验函数 handoff_errors 检查已读取报告、生产任务与消费任务，以及修复条目对应关系。

全量修复样例已对齐 finding-001；EChecker 已增加 finding_report 和报告内容，并提供独立的增量报告修复请求/响应样例。两条路径均加入契约回归校验。仍待实现：真实文件读取、摘要检查、实际仓库版本和运行结果验证。
