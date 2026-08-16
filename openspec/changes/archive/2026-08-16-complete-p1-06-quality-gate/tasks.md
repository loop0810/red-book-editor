## 1. 评测版本与 usage 契约

- [x] 1.1 在领域模型中增加可选模型 usage，并让 Agent diagnostics 汇总模型调用次数、prompt/completion/total token；保持旧调用方和 stub 兼容。
- [x] 1.2 让 DeepSeek adapter 安全解析供应商 usage，补充 adapter 和 Agent runtime 的单元测试，确保不保存原始响应消息。
- [x] 1.3 增加 prompt、style profile、Agent runtime 和评测配置的显式版本/摘要计算，创建当前案例集、scorecard 与门禁阈值 manifest。

## 2. Baseline runner 与自动指标

- [x] 2.1 将 baseline runner 升级到新 schema，记录 manifest context、usage、价格配置和估算成本，缺少 usage 时保留可诊断的空值而不伪造零。
- [x] 2.2 扩展自动评测逻辑，按来源事实计算每条记录的覆盖数量/比例，并汇总成功率、硬失败率、Agent 失败率、人工大改率、token 和成本指标。
- [x] 2.3 保持历史 schema 1/2/3 可由 `eval-validate` 读取，同时明确旧记录不能直接作为新质量门禁通过证据。

## 3. 阻断式质量门禁与对比报告

- [x] 3.1 实现候选 run 的 manifest、案例数量、重复次数、identity、usage 和成本证据校验。
- [x] 3.2 实现 scorecard 全量校验：六维分数、总分、硬失败、失败原因、人工最终修改稿和 reviewer note 必须完整一致。
- [x] 3.3 实现阈值检查和按案例/维度/诊断的 JSON 与 Markdown 报告，并支持与历史 run/score 做差异比较。
- [x] 3.4 增加 `make eval-quality-gate`，任一证据缺失、版本漂移或指标越界都返回非零退出码。

## 4. 测试、文档与验证

- [x] 4.1 增加质量门禁通过、阈值失败、版本漂移、事实覆盖不足、usage/成本缺失和人工评分不完整的单元测试。
- [x] 4.2 同步 `agent-evaluation`、`agent-quality-gate` 主 spec、评测 README/scorecard/baseline report、共享契约和 `docs/error/` 路线图/修复记录。
- [x] 4.3 执行 server lock-check、format-check、typecheck、unit tests、eval-validate、质量门禁 fixture、OpenSpec strict validation 和 diff check。
- [x] 4.4 使用本地 key 完成 schema 4 真实 baseline 和人工 scorecard 验证；记录门禁失败原因，删除不可用 baseline，并补充模型输出上限与中文事实覆盖回归测试。
