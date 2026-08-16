## Why

Milestone 3 的实现已经归档，但验证链路仍有三个缺口：字段建议集成测试仍断言旧响应、真实 baseline 的自动事实检查错误读取嵌套结果、以及部分案例因批评工具和最终校验不一致而耗尽 Agent 预算。现在修复这些问题，才能让后续 baseline 结果真正反映内容质量和运行时可靠性。

## What Changes

- 将字段重生成集成测试迁移到 `FieldSuggestion` 目标字段响应契约。
- 修正 baseline runner 的模块导入路径，并让自动硬失败检查兼容实际的嵌套最终输出。
- 收紧 critique 与最终事实校验的一致性，减少无效重复修订和预算耗尽。
- 清理会诱导医疗背书、疗效承诺或虚构结果的风格档案示例，并修正无关话题标签建议。
- 增加安全的来源事实分句匹配，允许自然中文改写但继续阻断来源外事实。
- 修正 `ai-editing-interactions` Purpose 文案，并将根目录 `key.json` 加入 Git 忽略。

## Capabilities

### New Capabilities

- `baseline-regression-gate`: 提供可执行、可诊断且不泄露敏感信息的 Agent baseline 回归验证能力。

### Modified Capabilities

- `fact-ledger-and-claim-audit`: 允许来源事实的安全自然改写，同时保持事实覆盖和来源外声明审核。
- `agent-runtime-workflow`: 要求 critique 的未解决事实/风格问题不能被误判为可定稿，避免进入无效重复循环。

## Impact

- 服务端：内容工作流事实匹配、critique/风格工具、风格 YAML、baseline hard-failure 检查、Makefile 和相关测试。
- 契约/文档：OpenSpec delta、`ai-editing-interactions` Purpose 和字段建议集成测试；不改变 HTTP 字段建议响应契约，不新增数据库 migration。
- 仓库安全：忽略本地 `key.json`，不读取或记录模型密钥内容。
