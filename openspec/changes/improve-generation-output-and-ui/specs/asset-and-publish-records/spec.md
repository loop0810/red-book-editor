## MODIFIED Requirements

### Requirement: Manage note assets

系统 SHALL 允许用户向笔记上传、预览、删除和排序图片素材，并保存配图建议；图片素材能力属于内容生产的辅助能力，不得替代或遮挡标题、正文和话题等核心结果。

#### Scenario: Attach and order images
- **WHEN** 用户为草稿上传多张图片并调整顺序
- **THEN** 系统保存图片与笔记的关联及排序，并在用户需要时按该顺序提供素材

#### Scenario: Invalid asset
- **WHEN** 用户上传系统不支持的文件类型或超过大小限制的文件
- **THEN** 系统拒绝该文件并显示可执行的错误信息，不影响已有文案和素材

### Requirement: Save draft versions

系统 SHALL 自动或显式保存笔记草稿，并允许用户恢复最近版本；版本历史和 Diff 属于次级能力，不得成为首次生成结果的默认信息区域。

#### Scenario: Recover a saved draft
- **WHEN** 用户离开编辑页后重新打开草稿
- **THEN** 系统恢复最近一次已保存的标题、正文、话题和素材状态

#### Scenario: Keep version history secondary
- **WHEN** 用户首次打开生成结果
- **THEN** 页面优先展示当前可编辑内容，不主动展开版本、Diff 或候选历史

### Requirement: Record manual publication

系统 SHALL 允许用户将笔记标记为待发布、已发布或不发布，并记录用户填写的发布时间、发布链接和备注；发布记录与表现数据属于内容发布后的次级复盘能力，不得出现在首次创作的主操作路径中。

#### Scenario: Mark as published
- **WHEN** 用户主动打开发布记录并填写发布时间，将草稿标记为已发布
- **THEN** 系统保存发布记录并将笔记状态更新为已发布

#### Scenario: Record performance metrics
- **WHEN** 用户主动为已发布笔记填写浏览、点赞、收藏、评论等数据
- **THEN** 系统保存这些数据并关联到对应的发布记录，供后续复盘使用

### Requirement: Protect account-scoped assets

系统 SHALL 对账号范围内的图片及其他内容素材使用访问控制，并在删除笔记或素材时明确告知用户删除影响；素材模型不得把育儿照片字段写成所有领域的固定前提。

#### Scenario: Isolate asset access
- **WHEN** 用户访问一个账号的素材库
- **THEN** 系统只返回该账号有权访问的素材
