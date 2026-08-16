## MODIFIED Requirements

### Requirement: Configure an account profile

系统 SHALL 允许用户创建并编辑账号配置，至少包含稳定的领域标识、账号定位、目标内容范围、表达风格、内容边界和常用表达；领域相关的附加配置由对应领域策略包定义，不能写死在通用账号表单中。

#### Scenario: Save account profile
- **WHEN** 用户填写有效的领域、账号定位和表达风格并保存
- **THEN** 系统保存配置，并在后续内容生成中使用同一账号的领域、定位、语气和边界

#### Scenario: Reject incomplete profile
- **WHEN** 用户缺少领域、账号定位或表达风格
- **THEN** 系统提示缺少字段且不保存为可用于生成的账号配置

#### Scenario: Preserve domain-specific account context
- **WHEN** 用户填写育儿领域的月龄等附加信息
- **THEN** 系统将其保存为育儿领域上下文，不要求其他领域也提供相同字段

### Requirement: Manage content columns

系统 SHALL 允许用户创建、编辑和停用内容栏目，并为每个栏目保存名称、说明和适合的内容类型；栏目属于账号和领域上下文，不得替代账号领域或被客户端固定 ID 静默替代。

#### Scenario: Use a selected column
- **WHEN** 用户在新建内容时选择一个启用的栏目
- **THEN** 系统将该栏目的说明和内容类型作为当前账号领域下的生成上下文

#### Scenario: Exclude inactive column
- **WHEN** 用户停用一个栏目
- **THEN** 该栏目不再出现在新建内容的可选列表中，但已有笔记仍保留其历史关联

#### Scenario: Resolve a real column identity
- **WHEN** 客户端发起生成
- **THEN** 请求使用服务端返回的真实栏目标识，不能依赖手工写入客户端的随机或环境相关栏目 ID

### Requirement: Preserve future account isolation

系统 SHALL 以账号标识隔离账号配置、领域上下文、栏目、笔记、素材和发布记录，使未来新增账号或领域时不会混用不同账号的创作上下文。

#### Scenario: Resolve content context by account
- **WHEN** 用户从某个账号工作台创建内容
- **THEN** 系统只加载该账号的领域、配置、栏目和素材作为默认上下文

#### Scenario: Do not leak another account's domain policy
- **WHEN** 两个账号使用不同领域或不同边界规则
- **THEN** 一个账号的领域提示、风格配置和安全策略不会被另一个账号的生成请求复用
