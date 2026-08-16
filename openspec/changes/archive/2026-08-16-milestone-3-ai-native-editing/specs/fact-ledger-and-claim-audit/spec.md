## MODIFIED Requirements

### Requirement: Audit generated claims against the source ledger

系统 SHALL 对标题、选题角度、正文、话题和封面文案中的关键声明执行来源审计，并为每条声明标记 `supported`、`uncertain` 或 `unsupported`，同时提供所属字段、来源证据或命中文本；无法从事实账本得到支持的声明不得被标记为 `supported`。

#### Scenario: Supported claim

- **WHEN** 生成内容准确表达了来源中的场景、做法或观察结果
- **THEN** 系统将该声明标记为 `supported`，关联对应的来源事实，并标明该声明所在字段

#### Scenario: Unsupported experience claim

- **WHEN** 生成内容加入来源没有提供的宴会细节、宝宝表现、产品效果或经历结果
- **THEN** 系统将该声明标记为 `unsupported`，记录命中文本和所属字段，并将草稿置于需要人工复核的状态

#### Scenario: Uncertain interpretation

- **WHEN** 生成内容是对来源事实的合理改写，但无法确认其是否表达了来源之外的确定结论
- **THEN** 系统将该声明标记为 `uncertain`，提供所属字段和复核原因，不得将草稿标记为 `ready`

### Requirement: Preserve and expose the audit snapshot

系统 SHALL 将事实审计结果作为审核结果的一部分随草稿返回，并在创建、保存、字段建议预览和生成版本恢复时保留；审核发现和声明审计必须能够关联到具体字段，并向编辑器提供来源证据或命中文本。旧草稿缺少事实账本或声明审计字段时必须兼容读取，并在下一次生成或保存时重新执行审核。

#### Scenario: Return claim audit with a generated draft

- **WHEN** 主生成、整篇风格重写或字段重生成完成
- **THEN** API 返回包含声明支持状态、字段、来源证据和风险级别的结构化审核快照

#### Scenario: Show evidence for a field

- **WHEN** 用户在编辑器查看正文、标题或其他生成字段的来源依据
- **THEN** 系统展示该字段相关声明的来源事实、证据文本或“未找到来源支持”的原因，不把模型生成内容加入确认事实

#### Scenario: Locate a review finding

- **WHEN** 审核发现命中风险或未支持声明
- **THEN** 系统返回所属字段和命中文本，客户端可以将用户带到对应字段复核；缺少字符范围时不得伪造精确高亮位置

#### Scenario: Recover an audited draft

- **WHEN** 用户重新打开已有草稿或历史版本
- **THEN** 系统恢复草稿内容及其最近一次审核快照，不把缺失的旧审计结果当作通过

#### Scenario: Re-audit edited content

- **WHEN** 用户修改任意生成字段或采纳字段建议后保存
- **THEN** 系统针对保存后的完整草稿重新建立声明审计，并使用新的结果计算草稿状态
