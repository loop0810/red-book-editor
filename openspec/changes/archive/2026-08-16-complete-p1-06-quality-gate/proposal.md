## Why

当前 baseline 能保存运行结果、硬失败标签和人工 scorecard，但没有统一的可计算事实覆盖率、版本/配置绑定或 token/成本证据；缺少证据的运行也可能被误认为质量通过。P1-06 需要一个可在本地和 CI 中执行、失败可诊断且默认阻断不合格结果的完整质量门禁。

## What Changes

- 增加版本化评测 manifest，绑定案例集、scorecard、system prompt、style profile、模型、Agent runtime 和门禁配置的摘要或版本。
- 扩展模型 usage 传递和 baseline 记录，保存 prompt/completion/total token 及按显式价格配置计算的估算成本；不保存 prompt、原始模型消息或密钥。
- 增加可解释的自动事实覆盖率、运行成功率、硬失败率、人工大改率和人工评分完整性检查，并为每项配置阈值。
- 增加候选 baseline 与历史 baseline 的按案例、维度和运行诊断对比报告，保留人工最终修改稿和失败运行。
- 增加 `make eval-quality-gate` 命令；输入、评分、版本绑定、usage 或阈值不满足时返回非零退出码，不能以缺失数据降级通过。
- 更新评测 README、scorecard、baseline report 和 `docs/error/` 修复记录，明确真实模型 baseline 需要使用本地 `key.json` 注入环境但不提交密钥。

## Capabilities

### New Capabilities

- `agent-quality-gate`: 定义评测 manifest、自动指标、阈值、人工评分完整性、成本约束和阻断式回归报告。

### Modified Capabilities

- `agent-evaluation`: 扩展运行记录的版本绑定和模型 usage 语义，保持历史 schema 可读取。

## Impact

- 服务端领域模型和 DeepSeek adapter：传递 token usage，保持业务层不依赖具体供应商格式。
- `server/scripts/`、`server/evals/agent_baseline/` 和 `server/Makefile`：新增 manifest、质量门禁、报告及测试。
- OpenSpec 主 specs、内容评测文档和 `docs/error/`：记录质量门禁已具备的证据边界及尚未覆盖的图片理解能力。
- 不修改生产笔记 schema，不持久化 prompt、原始消息、访问令牌、API key、图片或用户未脱敏内容。
