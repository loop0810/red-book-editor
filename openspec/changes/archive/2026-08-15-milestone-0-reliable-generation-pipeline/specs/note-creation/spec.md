## MODIFIED Requirements

### Requirement: Capture a source experience

系统 SHALL 允许用户记录宝宝月龄、发生场景、实际做法、观察结果、补充说明和可选图片素材，作为笔记创作的事实来源，并将其与可恢复的笔记草稿绑定保存。

#### Scenario: Create note from experience

- **WHEN** 用户提交一条包含场景和实际做法的育儿经历
- **THEN** 系统创建带有稳定笔记标识、账号和栏目标识的草稿，保留该经历作为可追溯的来源内容，并允许后续保存和重新打开

#### Scenario: Preserve user facts

- **WHEN** 系统根据经历生成笔记
- **THEN** 生成内容不得把用户未提供的关键经历、结果或个人体验呈现为已发生事实

### Requirement: Generate note components

系统 SHALL 基于账号配置、选定栏目、表达形式和事实来源生成选题角度、多个标题、正文、话题建议、封面文案和配图建议，并返回可保存的当前草稿版本。

#### Scenario: Generate a complete draft

- **WHEN** 用户提交有效的育儿经历并请求生成
- **THEN** 系统返回标题候选、正文、话题、封面文案和配图建议，草稿具有稳定标识和当前版本信息，且后续保存不需要重新创建笔记

#### Scenario: Use account and column context

- **WHEN** 用户从一个账号工作台的启用栏目发起生成
- **THEN** 系统使用该账号的定位、表达边界和该栏目的说明作为生成上下文，不使用固定或其他账号的上下文替代

#### Scenario: Handle generation failure

- **WHEN** 内容生成服务不可用或返回无法解析的结果
- **THEN** 系统保留用户输入，明确提示生成失败，并允许用户重试而不丢失经历或产生可导出的伪成功草稿

### Requirement: Edit and regenerate selectively

系统 SHALL 允许用户直接编辑笔记字段，并针对标题、正文、话题或封面文案单独重新生成，不得覆盖用户未选择修改的字段；草稿保存和恢复必须保留原先选择的表达形式。

#### Scenario: Edit one field

- **WHEN** 用户修改正文后保存
- **THEN** 系统保存新的草稿版本，并保留修改前版本可查看

#### Scenario: Regenerate selected field

- **WHEN** 用户请求重新生成标题
- **THEN** 系统只更新标题候选或当前标题，正文、话题、封面文案、来源事实和表达形式保持不变

#### Scenario: Recover selected style form

- **WHEN** 用户重新打开一个已保存的草稿并请求字段重生成且未另行选择表达形式
- **THEN** 系统使用该草稿保存的表达形式，不能因为跨端 DTO 或保存请求缺少字段而回退到默认形式
