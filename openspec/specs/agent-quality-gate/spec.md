# agent-quality-gate Specification

## Purpose

为内容 Agent 建立证据完整、可解释且可阻断的质量门禁，让自动事实和运行指标、人工评分、成本记录以及版本绑定能够共同决定一次 baseline 是否可接受。

## Requirements

### Requirement: Bind each evaluation to a versioned manifest

系统 SHALL 为每次评测记录案例集、scorecard、system prompt、style profile、模型、Agent runtime、评测配置和门禁配置的版本或内容摘要；门禁 SHALL 校验运行记录中的绑定与当前 manifest 一致，并且不得保存 prompt、模型原始消息、API key 或访问令牌。

#### Scenario: Reject a run with stale evaluation inputs

- **WHEN** 运行记录的案例集、scorecard、prompt、profile、模型或 Agent 配置摘要与 manifest 不一致
- **THEN** 质量门禁返回失败并指出不一致字段，不使用该运行的质量指标判定通过

#### Scenario: Keep evaluation metadata non-sensitive

- **WHEN** runner 生成运行记录或质量报告
- **THEN** 记录只包含版本、摘要、计数和脱敏诊断，不包含 prompt 正文、模型原始消息、密钥、访问令牌、图片内容或未脱敏用户正文

### Requirement: Calculate automatic quality metrics and enforce thresholds

系统 SHALL 对每条运行计算可解释的来源事实覆盖率，并汇总成功率、Agent 失败率、自动硬失败率、事实覆盖率、token 数和估算成本；门禁 SHALL 按 manifest 中的阈值检查这些指标，缺少运行、usage、成本或指标证据时 SHALL 判定失败而不是降级通过。

#### Scenario: Block an unsafe or incomplete baseline

- **WHEN** 候选 baseline 的自动硬失败、Agent 失败、事实覆盖率、成功率或成本超出 manifest 阈值
- **THEN** 质量门禁以非零退出码结束，并在报告中列出实际值、阈值和对应案例

#### Scenario: Count source fact coverage consistently

- **WHEN** 评测记录包含结构化最终草稿或失败记录
- **THEN** 系统按案例来源中可独立识别的事实计算覆盖数量和比例；失败或没有最终草稿的记录不得被当作事实覆盖完整

### Requirement: Require complete manual review evidence

系统 SHALL 要求候选 baseline 的每个 `case_id`/`attempt` 都有完整人工评分记录，六个 0～2 分维度、总分、硬失败标签、失败原因、人工最终修改稿和 reviewer note 必须存在且总分可由维度重算；缺失或不一致时门禁 SHALL 失败。

#### Scenario: Reject partial scorecard coverage

- **WHEN** 评分文件缺少某次运行、包含重复 identity、维度分数越界或总分不匹配
- **THEN** 质量门禁返回失败并指出具体 identity 和字段

#### Scenario: Include the final edited draft in review evidence

- **WHEN** 人工完成一条运行的评测
- **THEN** 评分记录保留可脱敏的最终修改稿和 reviewer note，即使原始 Agent 运行失败或需要大幅修改

### Requirement: Generate comparable baseline reports

系统 SHALL 生成当前 baseline 的总体指标、按案例指标、人工评分维度、运行诊断和门禁结果；当提供历史 baseline 时，报告 SHALL 生成按案例和评分维度的差异，且保留当前与历史的 run/score identity。

#### Scenario: Compare a candidate against the previous baseline

- **WHEN** 用户向质量门禁提供候选和历史 baseline
- **THEN** 报告列出成功率、事实覆盖率、硬失败、人工评分、人工大改率、token、成本及各案例的增减

### Requirement: Expose a blocking quality-gate command

系统 SHALL 提供一个从 `server/` 根目录可执行的 Make 目标，用于校验案例、运行、人工评分、manifest、阈值和报告；任何校验失败都必须返回非零退出码，所有检查通过才允许返回零。

#### Scenario: Pass a complete baseline

- **WHEN** 候选 baseline 的版本绑定、运行数量、usage、人工评分、指标和成本均满足阈值
- **THEN** 命令生成报告并以零退出码结束

#### Scenario: Fail closed when evidence is missing

- **WHEN** 未提供评分、token usage、成本价格或版本绑定证据
- **THEN** 命令生成失败报告并以非零退出码结束
