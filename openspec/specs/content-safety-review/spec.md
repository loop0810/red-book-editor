# content-safety-review Specification

## Purpose

在不破坏第一人称经验分享风格的前提下，对育儿笔记进行账号边界和高风险医疗内容检查，避免系统生成诊断、用药或虚构承诺。

## Requirements

### Requirement: Check account scope
系统 SHALL 检查草稿是否属于 0～2 岁育儿账号范围，并在明显偏离账号定位时提示用户调整，而不是静默生成无关内容。

#### Scenario: In-scope experience
- **WHEN** 草稿描述 0～2 岁宝宝的日常生活或护理经验
- **THEN** 系统允许进入编辑流程并不插入固定免责声明

#### Scenario: Out-of-scope topic
- **WHEN** 草稿主题明显超出账号年龄范围或内容边界
- **THEN** 系统标记偏离原因并要求用户确认或修改主题

### Requirement: Block diagnosis and medication advice
系统 SHALL 识别疾病判断、症状推理、药物名称、剂量、疗程和医疗效果承诺等内容，并阻止其作为普通经验笔记直接生成或导出。

#### Scenario: Common-care experience
- **WHEN** 用户描述感冒、发烧、尿布疹或湿疹相关的自身护理过程且不请求诊断或用药建议
- **THEN** 系统允许整理用户提供的事实和做法，同时标记该内容需要人工复核

#### Scenario: Diagnosis or medication request
- **WHEN** 用户请求判断疾病、推荐药物或给出用量
- **THEN** 系统不生成具体诊断或用药方案，并显示需要咨询专业医疗人员的提示

### Requirement: Detect fabricated or exaggerated content
系统 SHALL 检查生成稿是否包含来源中不存在的关键经历、保证性效果、绝对化结论或制造焦虑的表达。

#### Scenario: Unsupported claim
- **WHEN** 生成稿声称某做法一定有效，但用户来源没有提供该结果
- **THEN** 系统标记该句为待修改内容，并不将其视为已通过检查

#### Scenario: Passed review
- **WHEN** 草稿没有检测到阻断级风险
- **THEN** 系统显示检查通过或提示级问题，并允许用户继续编辑和复制
