## Purpose

为单一小红书育儿账号提供可持续复用的定位、风格、内容范围和栏目配置，使后续每篇笔记都能基于同一账号上下文创作。

## ADDED Requirements

### Requirement: Configure an account profile
系统 SHALL 允许用户创建并编辑一个账号配置，至少包含账号定位、目标内容年龄范围、当前宝宝月龄、表达风格、内容边界和常用表达。

#### Scenario: Save account profile
- **WHEN** 用户填写必填的账号定位、年龄范围和表达风格并保存
- **THEN** 系统保存配置并在后续创作中使用该配置

#### Scenario: Reject incomplete profile
- **WHEN** 用户缺少账号定位或内容年龄范围
- **THEN** 系统提示缺少字段且不保存为可用账号配置

### Requirement: Manage content columns
系统 SHALL 允许用户创建、编辑和停用内容栏目，并为每个栏目保存名称、说明和适合的内容类型。

#### Scenario: Use a selected column
- **WHEN** 用户在新建笔记时选择一个启用的栏目
- **THEN** 系统将该栏目的说明和内容类型作为生成上下文

#### Scenario: Exclude inactive column
- **WHEN** 用户停用一个栏目
- **THEN** 该栏目不再出现在新建笔记的可选列表中，但已有笔记仍保留其历史关联

### Requirement: Preserve future account isolation
系统 SHALL 以账号标识隔离账号配置、栏目、笔记、素材和发布记录，使未来新增账号时不会混用不同账号的创作上下文。

#### Scenario: Resolve content context by account
- **WHEN** 用户从某个账号工作台创建笔记
- **THEN** 系统只加载该账号的配置、栏目和素材作为默认上下文
