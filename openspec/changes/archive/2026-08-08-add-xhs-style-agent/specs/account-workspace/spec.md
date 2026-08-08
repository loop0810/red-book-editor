## MODIFIED Requirements

### Requirement: Configure an account profile
系统 SHALL 允许用户创建并编辑一个账号配置，至少包含账号定位、目标内容年龄范围、当前宝宝月龄、表达风格、内容边界和常用表达；V1 账号定位 SHALL 覆盖备孕 → 孕检 → 育儿全程。

#### Scenario: Save account profile
- **WHEN** 用户填写必填的账号定位、年龄范围和表达风格并保存
- **THEN** 系统保存配置并在后续创作中使用该配置

#### Scenario: Reject incomplete profile
- **WHEN** 用户缺少账号定位或内容年龄范围
- **THEN** 系统提示缺少字段且不保存为可用账号配置

#### Scenario: Cover full journey
- **WHEN** 用户将账号定位配置为备孕-孕检-育儿全程记录
- **THEN** 系统接受该定位并允许在备孕、孕检、育儿主题下创建笔记

### Requirement: Manage content columns
系统 SHALL 提供三种表达形式栏目预设（科普、经验、软文），允许用户创建、编辑和停用内容栏目，并为每个栏目保存名称、说明和适合的内容类型；V1 所选栏目 SHALL 作为风格转换的表达形式依据。

#### Scenario: Three form presets
- **WHEN** 用户首次进入账号工作台
- **THEN** 系统提供科普、经验、软文三个栏目预设，可直接启用使用

#### Scenario: Use a selected column
- **WHEN** 用户在新建笔记时选择一个启用的栏目
- **THEN** 系统将该栏目的说明和内容类型作为风格转换上下文

#### Scenario: Exclude inactive column
- **WHEN** 用户停用一个栏目
- **THEN** 该栏目不再出现在新建笔记的可选列表中，但已有笔记仍保留其历史关联

