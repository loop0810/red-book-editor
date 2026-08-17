## MODIFIED Requirements

### Requirement: Audit generated claims against the source ledger

系统 SHALL 对标题、选题角度、正文、话题和封面文案中的关键声明执行来源审计，并为内部质量流程记录 `supported`、`uncertain` 或 `unsupported`、来源证据和字段信息；来源审计结果不是普通 C 端页面的逐条内容，也不能仅凭脆弱的逐字匹配把自然改写视为用户错误。

#### Scenario: Supported claim
- **WHEN** 生成内容准确表达了来源中的主题、场景、做法或观察结果
- **THEN** 系统将该声明标记为 `supported`，并关联对应来源事实

#### Scenario: Unsupported experience claim
- **WHEN** 生成内容加入来源没有提供的关键宴会细节、宝宝表现、产品效果或经历结果
- **THEN** 系统将该声明标记为 `unsupported`，记录内部证据，并根据领域策略决定是否阻断；普通用户只收到必要的字段级修改提示

#### Scenario: Uncertain interpretation
- **WHEN** 生成内容是对来源事实的合理改写，但无法确认其是否表达了来源之外的确定结论
- **THEN** 系统保留 `uncertain` 内部状态，并不得自动显示疾病/用药等无关提示；是否影响 `ready` 由当前领域策略决定

### Requirement: Preserve and expose the audit snapshot

系统 SHALL 在创建、保存和版本恢复时保留当前版本的事实审计快照，供服务端质量、导出门禁、评测和授权调试使用；普通 C 端响应只返回必要的用户结果和可行动问题投影，不返回完整声明证据、命中文本或 Fact Ledger。

#### Scenario: Keep an internal audit snapshot
- **WHEN** 主生成、整篇重写或字段重生成完成
- **THEN** 服务端保存与当前草稿版本绑定的审计快照，并可供内部质量流程读取

#### Scenario: Keep field-scoped internal evidence
- **WHEN** 用户请求局部字段候选
- **THEN** 服务端可以用完整候选草稿执行内部审核，但用户响应只返回目标字段候选和必要的可行动状态

#### Scenario: Recover an audited draft
- **WHEN** 用户重新打开已有草稿或历史版本
- **THEN** 系统恢复草稿及其内部审核快照；缺失或过期快照由服务端重新审核，不把内部结构直接展示给用户

#### Scenario: Re-audit edited content
- **WHEN** 用户修改任意生成字段后保存
- **THEN** 系统针对保存后的完整草稿重新建立内部声明审计，并使用领域策略重新计算状态和导出门禁
