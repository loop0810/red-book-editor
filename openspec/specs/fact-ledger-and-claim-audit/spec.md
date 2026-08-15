# fact-ledger-and-claim-audit Specification

## Purpose

为每篇笔记建立可追溯的来源事实边界，并审计生成内容中的关键声明，防止用户未提供的经历、结果或安全结论被当作真实事实输出。

## Requirements

### Requirement: Build a source fact ledger

系统 SHALL 根据用户提交的 SourceExperience 建立结构化事实账本，至少区分用户明确提供的事实、用户观察到的结果、用户个人观点、未知信息和禁止推断边界；系统不得把模型生成的内容加入已确认事实。

#### Scenario: Record source facts with provenance

- **WHEN** 用户提交包含月龄、场景、实际做法和观察结果的经历
- **THEN** 系统为每项来源内容记录可追溯的来源位置和事实类别，并保留原始来源内容

#### Scenario: Keep unknown facts outside confirmed facts

- **WHEN** 来源没有提供药物名称、剂量、环境、产品属性、宴会细节或确定结果
- **THEN** 系统将这些信息视为未知或禁止推断内容，不得在事实账本中标记为已确认

### Requirement: Audit generated claims against the source ledger

系统 SHALL 对标题、选题角度、正文、话题和封面文案中的关键声明执行来源审计，并为每条声明标记 `supported`、`uncertain` 或 `unsupported`，同时提供来源证据或命中文本；无法从事实账本得到支持的声明不得被标记为 `supported`。

#### Scenario: Supported claim

- **WHEN** 生成内容准确表达了来源中的场景、做法或观察结果
- **THEN** 系统将该声明标记为 `supported`，并关联对应的来源事实

#### Scenario: Unsupported experience claim

- **WHEN** 生成内容加入来源没有提供的宴会细节、宝宝表现、产品效果或经历结果
- **THEN** 系统将该声明标记为 `unsupported`，记录命中文本，并将草稿置于需要人工复核的状态

#### Scenario: Uncertain interpretation

- **WHEN** 生成内容是对来源事实的合理改写，但无法确认其是否表达了来源之外的确定结论
- **THEN** 系统将该声明标记为 `uncertain`，不得将草稿标记为 `ready`

### Requirement: Preserve and expose the audit snapshot

系统 SHALL 将事实审计结果作为审核结果的一部分随草稿返回，并在创建、保存和生成版本恢复时保留；旧草稿缺少事实账本或声明审计字段时必须兼容读取，并在下一次生成或保存时重新执行审核。

#### Scenario: Return claim audit with a generated draft

- **WHEN** 主生成、整篇重写或字段重生成完成
- **THEN** API 返回包含声明支持状态、来源证据和风险级别的结构化审核快照

#### Scenario: Recover an audited draft

- **WHEN** 用户重新打开已有草稿或历史版本
- **THEN** 系统恢复草稿内容及其最近一次审核快照，不把缺失的旧审计结果当作通过

#### Scenario: Re-audit edited content

- **WHEN** 用户修改任意生成字段后保存
- **THEN** 系统针对保存后的完整草稿重新建立声明审计，并使用新的结果计算草稿状态
