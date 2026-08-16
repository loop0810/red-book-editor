## Context

当前 `run_agent_eval.py` 只记录 schema 3 的运行结果和 Agent diagnostics，DeepSeek adapter 丢弃供应商返回的 usage；人工 scorecard 与 run 通过独立 JSON 关联，缺少完整性和版本一致性校验。P1-06 需要保持旧 run 可读，同时让新 run 在进入质量门禁前拥有足够证据。

## Goals / Non-Goals

**Goals:**

- 以一个提交到仓库的 manifest 固定案例集、scorecard、prompt、profile、Agent 配置和阈值的身份。
- 将模型 usage 通过领域端口传到 evaluator，并在不保存模型消息的前提下计算 token 和估算成本。
- 计算事实覆盖率、运行稳定性、硬失败、人工评分和修改成本，生成 JSON/Markdown 对比报告。
- 提供 fail-closed 的 `make eval-quality-gate`，支持候选 baseline 与历史 baseline 对比。

**Non-Goals:**

- 不自动替代人工判断，也不把文本匹配事实覆盖率宣称为完整语义事实理解。
- 不修改生产数据库、Note 状态、模型 prompt 内容或图片理解能力。
- 不在本 change 中调用真实模型生成新的 baseline；真实运行由使用者在本地提供 key 和价格配置后执行。

## Decisions

### 1. 使用内容摘要而不是把 prompt 或原始消息写进评测记录

runner 对案例 JSON、scorecard、system prompt、style profile 和 Agent 配置计算 SHA-256，并把摘要及显式版本写入 manifest/context。这样可以发现评测输入漂移，又不会把敏感上下文复制到 run 文件。

备选方案是把完整 prompt 保存到每个 run，诊断更方便但违反现有隐私边界；不绑定版本则无法判断历史分数是否仍可比较。

### 2. 在 `ModelResponse` 中增加可选 usage，并由 Agent diagnostics 汇总

usage 是模型供应商响应的跨层事实，因此在领域端口增加可选 `ModelUsage`，DeepSeek adapter 只做字段映射，AgentRuntime 汇总每次调用的 token。stub 或旧供应商没有 usage 时保留 `None`，质量门禁对真实模型缺失 usage 直接失败。

备选方案是只在 DeepSeek evaluator 中解析 HTTP JSON，会让评测绕过领域端口且无法复用到 AgentRun；将供应商原始响应写入记录则泄露消息内容并耦合领域逻辑。

### 3. 用 manifest 驱动阈值，报告与退出码共用同一结果

manifest 保存阈值和 expected digests；quality gate 先验证输入，再计算统一的 metrics/checks，最后同时写 JSON/Markdown 报告和返回退出码。报告不会另行“美化”失败结果，避免 CI 和人工阅读得到不同结论。

默认阈值要求运行成功、自动硬失败为零、事实覆盖达到 100%、人工平均分达到项目门槛、人工大改为零且成本不超过预算；阈值可在 manifest 中显式调整，缺失值不是放宽条件。

### 4. 评分文件按 run identity 做全量校验

quality gate 将 `(case_id, attempt)` 作为唯一键，要求候选 run 和 score 一一对应，校验六个维度、总分、hard failures、failure reason、final edited draft 和 reviewer note。历史 schema 继续由 `eval-validate` 读取，但不自动获得新质量门禁通过资格。

### 5. 将模型输出上限纳入评测身份

真实模型运行通过 `MODEL_MAX_TOKENS` 设置输出上限，runner 将该值写入 evaluation context，manifest 绑定为当前评测配置的一部分。这样同一模型但不同输出预算不会被误认为可直接比较；本地 key 和价格仍只通过进程环境注入。

### 6. 事实覆盖只做窄范围中文归一化

事实覆盖检查仅在来源事实与输出之间去除中文体貌助词“了/啦”，用于识别“举行周岁宴/举行了周岁宴”这类表面变化；不扩展为开放式同义词或语义推断，仍由人工评分负责最终判断。

## Risks / Trade-offs

- [文本匹配不能理解所有同义改写] → 将覆盖率标为自动初筛指标，并保留人工 scorecard；严格阈值缺证据时失败，不宣称语义完备。
- [模型供应商价格会变化] → 价格只从显式运行配置读取并写入 context；缺失价格时 cost gate 失败，更新价格不修改历史 run。
- [旧 run 缺少 usage 和版本摘要] → 保持旧 validator 可读，但质量 gate 明确拒绝旧 schema 作为当前通过证据。
- [阈值过严导致本地迭代频繁失败] → 所有失败项输出实际值和 identity，允许在 manifest 中经过评审后显式调整，而不是静默降级。

## Migration Plan

1. 先部署领域 usage、manifest 和 evaluator；不需要数据库 migration。
2. 使用同一批脱敏案例重新运行并人工补齐 score 文件，再执行 `make eval-quality-gate`。
3. 只有通过门禁的 JSON/Markdown 报告才作为评测记录保留；失败候选和不可用旧 runs/scores 可以按项目清理要求删除，摘要写入 baseline report。
4. 回滚时可停止调用新 gate，生产内容流程不受影响；删除新 evaluator 文件不会影响历史 JSON 的读取。
