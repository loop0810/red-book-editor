## MODIFIED Requirements

### Requirement: Block diagnosis and medication advice
系统 SHALL 识别疾病判断、症状推理、药物名称、剂量、疗程和医疗效果承诺等内容；V1 风格转换路径 SHALL 不自动阻断这些内容，而是直接进入用户人工确认流程，检查能力保留供后续版本启用。

#### Scenario: Common-care experience
- **WHEN** 用户描述感冒、发烧、尿布疹或湿疹相关的自身护理过程且不请求诊断或用药建议
- **THEN** 系统允许整理用户提供的事实和做法，并标记该内容需要人工复核

#### Scenario: V1 styling path bypasses blocking
- **WHEN** 风格转换草稿包含剂量、就医建议或专家背书等育儿领域常见写法
- **THEN** 系统不自动阻断，草稿直接进入用户人工确认流程

### Requirement: Detect fabricated or exaggerated content
系统 SHALL 检查生成稿是否包含来源中不存在的关键经历、保证性效果、绝对化结论或制造焦虑的表达；风格转换 agent 的"事实保持"核对 SHALL 在自评阶段执行，V1 不因发现此类内容而阻断导出。

#### Scenario: Unsupported claim in styling
- **WHEN** 风格转换稿引入源经历不存在的关键经历或外部背书
- **THEN** agent 在自评阶段识别并要求修订，最终输出不含未支持的已发生陈述

#### Scenario: Warning-level language
- **WHEN** 草稿包含保证性效果或焦虑表达
- **THEN** V1 不阻断导出，由用户人工判断
