# note-creation Specification

## Purpose

帮助用户用账号定位、明确主题和原始素材生成可编辑、可复制的小红书内容；领域专属信息作为可选上下文，不应改变内容优先的主流程。

## Requirements

### Requirement: Capture a content brief

系统 SHALL 允许用户记录本次内容的明确主题/重心、原始素材和可选图片，并允许当前领域策略包补充结构化上下文；通用创作流程不得要求用户先填写育儿专属经历字段。

#### Scenario: Create note from a focused brief
- **WHEN** 用户提交“宝宝周岁宴”等明确主题以及相关原始素材
- **THEN** 系统创建带有稳定笔记标识、账号和栏目标识的草稿，并保留主题与原始素材作为可追溯来源

#### Scenario: Preserve user facts and focus
- **WHEN** 系统根据内容简报生成笔记
- **THEN** 生成内容不得把用户未提供的关键经历、结果或个人体验呈现为已发生事实，标题和选题角度必须优先围绕用户明确的主题，不能把限制条件自动提升为主题

#### Scenario: Add domain context without changing the core brief
- **WHEN** 育儿领域需要月龄或照护场景等补充信息
- **THEN** 系统将这些信息作为领域上下文参与生成，但主题和原始素材仍是所有领域通用的主要输入

### Requirement: Generate note components

系统 SHALL 基于账号领域、账号定位、选定栏目、表达风格、内容主题、原始素材和领域上下文生成标题候选、正文、话题、配图建议以及可选封面文案，并返回可保存的当前草稿版本。

#### Scenario: Generate a complete draft
- **WHEN** 用户提交有效的内容主题和原始素材并请求生成
- **THEN** 系统返回标题候选、正文、话题和配图建议，草稿具有稳定标识和当前版本信息，且标题候选至少有一个明确体现用户主题

#### Scenario: Use account and domain context
- **WHEN** 用户从一个账号工作台的启用栏目发起生成
- **THEN** 系统使用该账号的领域、定位、表达边界、栏目说明和所选表达风格作为生成上下文，不使用固定或其他账号的上下文替代

#### Scenario: Handle generation failure
- **WHEN** 内容生成服务不可用或返回无法解析的结果
- **THEN** 系统保留用户输入，向用户显示简洁且可执行的失败提示，并允许用户重试而不丢失素材或产生可复制的伪成功草稿

#### Scenario: Reach creation from first-use onboarding
- **WHEN** 工作台尚未配置账号或启用栏目
- **THEN** 用户可以从首页进入账号/栏目配置；配置完成后回到内容创建流程，不需要先完成登录注册

### Requirement: Edit and regenerate selectively

系统 SHALL 允许用户直接编辑笔记字段，并针对标题、正文、话题或封面文案单独请求一个不自动覆盖当前草稿的 AI 候选；候选历史、Diff 和内部审核证据可以由系统保存，但不属于生成页面的默认用户流程。

#### Scenario: Edit one field
- **WHEN** 用户修改正文后保存
- **THEN** 系统保存新的草稿版本，并保留修改前版本供后续恢复

#### Scenario: Regenerate selected field
- **WHEN** 用户请求重新生成标题
- **THEN** 系统只返回标题候选，正文、话题、配图建议、来源素材、当前用户编辑和表达风格保持不变

#### Scenario: Accept a field suggestion
- **WHEN** 用户明确采纳一个没有基础冲突的字段候选
- **THEN** 系统只将候选值合并到目标字段，其他字段保持不变，并在保存时重新执行服务端质量与安全校验

#### Scenario: Recover a failed generation
- **WHEN** 异步生成失败、取消或连接中断
- **THEN** 系统保留运行引用和内容简报，允许用户继续运行或重新生成；失败运行不得作为成功草稿打开，用户页面只显示重试或继续操作，不显示内部阶段 trace

#### Scenario: Recover selected style form
- **WHEN** 用户重新打开已保存草稿并请求字段重生成且未另行选择表达形式
- **THEN** 系统使用草稿保存的表达形式，不能因为跨端 DTO 或保存请求缺少字段而回退到默认形式

### Requirement: Copy note for manual publishing

系统 SHALL 提供复制标题、复制正文、复制话题和使用配图建议/素材的操作；系统不得在 V1 中自动登录或发布到小红书。

#### Scenario: Copy publish content
- **WHEN** 用户点击复制标题、正文或话题
- **THEN** 系统将对应内容写入剪贴板并显示简短成功反馈

#### Scenario: Manual publishing boundary
- **WHEN** 用户完成笔记编辑
- **THEN** 系统只提供复制、保存和素材使用能力，不触发小红书账号登录、发布、点赞或评论操作

### Requirement: Keep the primary result user-facing

系统 SHALL 将生成结果页面聚焦于可直接使用的标题、正文、话题和配图建议；Agent trace、模型步骤、Fact Ledger、Claim Audit、内部规则名称和详细命中文本不得出现在普通用户的主创作流程中。

#### Scenario: Open a successful result
- **WHEN** 生成成功并进入编辑页面
- **THEN** 用户首先看到可编辑的内容结果和复制/保存操作，而不是 Agent 执行过程或审核诊断

#### Scenario: Show a real blocking issue
- **WHEN** 服务端判定存在需要用户处理的真实阻断问题
- **THEN** 页面只显示与该问题对应的简短、可行动提示，并能定位到需要修改的字段，不显示无关的领域规则列表
