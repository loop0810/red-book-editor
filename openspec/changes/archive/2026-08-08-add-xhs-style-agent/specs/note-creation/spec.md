## MODIFIED Requirements

### Requirement: Generate note components
系统 SHALL 基于账号配置、选定表达形式和事实来源先生成中性草稿，再通过风格转换 agent 产出小红书风格化的选题角度、多个标题、正文、话题、封面文案和配图建议，并在响应中附带 agent 逐步 trace；V1 风格化路径的草稿状态不由阻断级内容检查决定。

#### Scenario: Generate a complete styled draft
- **WHEN** 用户提交有效的育儿经历、选择表达形式并请求生成
- **THEN** 系统返回风格化标题候选、正文、话题、封面文案、配图建议、草稿状态与 agent trace

#### Scenario: Handle generation failure
- **WHEN** 内容生成服务不可用或返回无法解析的结果
- **THEN** 系统保留用户输入，明确提示生成失败，并允许用户重试而不丢失经历

#### Scenario: Style conversion without blocking review
- **WHEN** 风格化草稿包含育儿领域常见写法（如就医红线、专家背书）
- **THEN** V1 不触发阻断级检查，草稿直接进入用户人工确认流程

## ADDED Requirements

### Requirement: Select an expression form
系统 SHALL 在新建笔记时允许用户选择表达形式（科普 / 经验 / 软文），该选择 SHALL 作为风格转换依据，并在局部重新生成时保持不变。

#### Scenario: Pick form before generation
- **WHEN** 用户新建笔记并选择"经验"表达形式
- **THEN** 风格转换按经验档案执行

#### Scenario: Regeneration keeps form
- **WHEN** 用户对已风格化草稿局部重新生成某个字段
- **THEN** 重新生成仍使用原表达形式，且不覆盖未选择的字段

