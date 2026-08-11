# asset-and-publish-records Specification

## Purpose

为笔记提供图片素材、草稿版本、手动发布状态和基础数据记录，使用户能够从创作一直追踪到发布后的复盘，并在发布后持续沉淀可回顾的内容表现信息。

## Requirements

### Requirement: Manage note assets
系统 SHALL 允许用户向笔记上传、预览、删除和排序图片素材，并保存封面文案和配图建议。

#### Scenario: Attach and order images
- **WHEN** 用户为草稿上传多张图片并调整顺序
- **THEN** 系统保存图片与笔记的关联及排序，并在导出时按该顺序提供素材

#### Scenario: Invalid asset
- **WHEN** 用户上传系统不支持的文件类型或超过大小限制的文件
- **THEN** 系统拒绝该文件并显示可执行的错误信息，不影响已有素材

### Requirement: Save draft versions
系统 SHALL 自动或显式保存笔记草稿，并允许用户查看当前版本和此前版本。

#### Scenario: Recover a saved draft
- **WHEN** 用户离开编辑页后重新打开草稿
- **THEN** 系统恢复最近一次已保存的标题、正文、话题和素材状态

### Requirement: Record manual publication
系统 SHALL 允许用户将笔记标记为待发布、已发布或不发布，并记录用户填写的发布时间、发布链接和备注。

#### Scenario: Mark as published
- **WHEN** 用户填写发布时间并将草稿标记为已发布
- **THEN** 系统保存发布记录并将笔记从待发布状态更新为已发布

#### Scenario: Record performance metrics
- **WHEN** 用户为已发布笔记填写浏览、点赞、收藏、评论等数据
- **THEN** 系统保存这些数据并关联到对应的发布记录，供后续复盘使用

### Requirement: Protect child-related assets
系统 SHALL 对宝宝照片和相关素材使用账号范围内的访问控制，并在删除笔记或素材时明确告知用户删除影响。

#### Scenario: Isolate asset access
- **WHEN** 用户访问一个账号的素材库
- **THEN** 系统只返回该账号有权访问的素材
