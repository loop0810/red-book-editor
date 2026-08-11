## Purpose

帮助用户把关于 0～2 岁宝宝的真实经历整理成自然的小红书图文笔记，并支持多轮编辑、保存和复制使用。

## ADDED Requirements

### Requirement: Capture a source experience
系统 SHALL 允许用户记录宝宝月龄、发生场景、实际做法、观察结果、补充说明和可选图片素材，作为笔记创作的事实来源。

#### Scenario: Create note from experience
- **WHEN** 用户提交一条包含场景和实际做法的育儿经历
- **THEN** 系统创建笔记草稿并保留该经历作为可追溯的来源内容

#### Scenario: Preserve user facts
- **WHEN** 系统根据经历生成笔记
- **THEN** 生成内容不得把用户未提供的关键经历、结果或个人体验呈现为已发生事实

### Requirement: Generate note components
系统 SHALL 基于账号配置、选定栏目和事实来源生成选题角度、多个标题、正文、话题建议、封面文案和配图建议。

#### Scenario: Generate a complete draft
- **WHEN** 用户提交有效的育儿经历并请求生成
- **THEN** 系统返回标题候选、正文、话题、封面文案和配图建议，并标记当前草稿版本

#### Scenario: Handle generation failure
- **WHEN** 内容生成服务不可用或返回无法解析的结果
- **THEN** 系统保留用户输入，明确提示生成失败，并允许用户重试而不丢失经历

### Requirement: Edit and regenerate selectively
系统 SHALL 允许用户直接编辑笔记字段，并针对标题、正文、话题或封面文案单独重新生成，不得覆盖用户未选择修改的字段。

#### Scenario: Edit one field
- **WHEN** 用户修改正文后保存
- **THEN** 系统保存新的草稿版本，并保留修改前版本可查看

#### Scenario: Regenerate selected field
- **WHEN** 用户请求重新生成标题
- **THEN** 系统只更新标题候选或当前标题，正文、话题和封面文案保持不变

### Requirement: Copy note for manual publishing
系统 SHALL 提供复制标题、复制正文、复制话题和导出或下载素材的操作；系统不得在 V1 中自动登录或发布到小红书。

#### Scenario: Copy publish content
- **WHEN** 用户点击复制标题或正文
- **THEN** 系统将对应内容写入剪贴板并显示成功反馈

#### Scenario: Manual publishing boundary
- **WHEN** 用户完成笔记编辑
- **THEN** 系统只提供复制和素材导出能力，不触发小红书账号登录、发布、点赞或评论操作
