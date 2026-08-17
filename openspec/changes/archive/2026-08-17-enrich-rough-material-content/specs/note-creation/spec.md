## MODIFIED Requirements

### Requirement: Capture a content brief

系统 SHALL 允许用户提供本次内容的明确主题/重心、粗略原始素材和可选图片；原始素材可以是关键词、流水账、口语化片段或不完整描述，不要求用户先写成可发布正文。通用创作流程不得要求用户先填写育儿专属经历字段。

#### Scenario: Create note from rough material
- **WHEN** 用户提交“宝宝周岁”等明确主题以及几句粗略的过程描述
- **THEN** 系统创建带有稳定笔记标识、账号和栏目标识的草稿，并保留主题与原始素材作为可追溯来源

#### Scenario: Preserve facts without preserving wording
- **WHEN** 系统根据内容简报生成笔记
- **THEN** 生成内容 MUST 保留用户提供的关键事实、关系和限制条件，但不得要求复用原始句子或原始段落结构；标题和选题角度必须优先围绕用户明确的主题，不能把限制条件自动提升为主题

#### Scenario: Add domain context without changing the core brief
- **WHEN** 育儿领域需要月龄或照护场景等补充信息
- **THEN** 系统将这些信息作为领域上下文参与生成，但主题和原始素材仍是所有领域通用的主要输入

### Requirement: Generate note components

系统 SHALL 基于账号领域、账号定位、选定栏目、表达风格、内容主题、粗略原始素材和领域上下文生成标题候选、正文、话题、配图建议以及可选封面文案，并返回可保存的当前草稿版本。生成过程 MUST 将原始素材重新组织为可直接编辑和使用的小红书风格内容，而不是把素材当作现成正文进行扩写或拼接。

#### Scenario: Generate a complete draft from concise input
- **WHEN** 用户只提交几句简短、口语化或结构不完整的内容主题和素材
- **THEN** 系统返回具有清晰开头、过程细节、内容收束和小红书表达结构的标题候选、正文、话题和配图建议；标题候选至少有一个明确体现用户主题

#### Scenario: Enrich expression without inventing experience
- **WHEN** 系统需要将粗略素材丰富成完整文案
- **THEN** 系统可以增加连接句、段落结构、叙事钩子、编辑性总结和不改变事实的适度情绪表达，但不得虚构用户未提供的具体事件、人物、结果、时间线或个人经历

#### Scenario: Rewrite the opening instead of copying the source
- **WHEN** 原始素材包含一段可直接复用的用户文字
- **THEN** 生成正文的第一段 MUST 经过重新组织并承担新的内容入口或叙事钩子，不得直接复制原始素材作为开头；正文整体不得只是将原文拆段或重复粘贴后增加少量连接词

#### Scenario: Keep source facts while changing the presentation
- **WHEN** 生成内容对原始素材进行改写、调序或合并
- **THEN** 系统 MUST 保留关键事实和限制条件的可追溯性，并允许合并低价值重复表述；事实保真校验不得以“逐字复现原句”作为唯一通过条件

#### Scenario: Use account and domain context
- **WHEN** 用户从一个账号工作台的启用栏目发起生成
- **THEN** 系统使用该账号的领域、定位、表达边界、栏目说明和所选表达风格作为生成上下文，不使用固定或其他账号的上下文替代

#### Scenario: Handle generation failure
- **WHEN** 内容生成服务不可用或返回无法解析的结果
- **THEN** 系统保留用户输入，向用户显示简洁且可执行的失败提示，并允许用户重试而不丢失素材或产生可复制的伪成功草稿

#### Scenario: Reach creation from first-use onboarding
- **WHEN** 工作台尚未配置账号或启用栏目
- **THEN** 用户可以从首页进入账号/栏目配置；配置完成后回到内容创建流程，不需要先完成登录注册
