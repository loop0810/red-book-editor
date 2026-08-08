## Purpose

将中性草稿转换为小红书风格育儿文案：按表达形式（科普 / 经验 / 软文）加载风格档案，由 agent 完成规划、写作、自评与修订，并应用富文本装饰与逐步 trace。

## ADDED Requirements

### Requirement: Maintain expression-form style profiles
系统 SHALL 以服务端代码库内版本化 YAML 文件维护三种表达形式的风格档案（科普、经验、软文），每个档案定义标题钩子模式、正文结构模板、语气与情绪词、emoji/符号规则、话题标签池、封面文案模式与 CTA 模式。

#### Scenario: Load profile by form
- **WHEN** 用户选择"科普"并请求风格转换
- **THEN** 系统加载科普档案并据此转换，其他表达形式档案不影响本次输出

#### Scenario: Unknown form
- **WHEN** 请求使用未定义的表达形式名称
- **THEN** 请求被拒绝并返回校验错误

### Requirement: Convert draft to styled note
系统 SHALL 按选定表达形式将中性草稿重写为小红书风格草稿，重写范围包括标题候选、正文、话题、封面文案与配图建议，并保持 `SourceExperience` 中的关键事实不变，不得把用户未提供的经历、结果或专家观点呈现为已发生事实。

#### Scenario: Successful conversion
- **WHEN** 用户对草稿请求按某表达形式转换
- **THEN** 返回风格化草稿，标题、正文、话题、封面文案全部按该形式档案改写，关键事实与源经历一致

#### Scenario: Fact preservation violation
- **WHEN** 模型在重写中引入源经历不存在的事实或外部背书
- **THEN** 系统通过自评/事实核对步骤识别并修订，最终输出不得包含未支持的已发生陈述

### Requirement: Self-critique and revise
系统 SHALL 在输出最终草稿前对照风格档案执行至少一次自评（钩子、结构、语气、事实保持），并在自评未达标时修订草稿。

#### Scenario: Critique loop
- **WHEN** 自评发现钩子或结构不符合所选档案
- **THEN** agent 修订草稿后再次自评，直到达标或达到修订上限

### Requirement: Decorate with rich text
系统 SHALL 应用富文本装饰：按档案规则添加 emoji/分隔符号、三层话题标签（泛标签、精准标签、蹭热点标签）与 CTA 结尾，话题数量在档案定义范围内。

#### Scenario: Three-layer tags
- **WHEN** 输出话题建议
- **THEN** 话题包含泛标签、精准标签与蹭热点标签的组合，数量符合档案范围

#### Scenario: Cover copy
- **WHEN** 输出封面文案
- **THEN** 封面文案符合该表达形式的短句模式（如数字+事件、权威背书+结果）

### Requirement: Return conversion trace
系统 SHALL 在风格转换响应中返回 agent 逐步 trace（读取档案、规划、写作、自评、修订等），供客户端展示。

#### Scenario: Styled response includes trace
- **WHEN** 风格转换成功
- **THEN** 响应包含风格化草稿和按执行顺序排列的 trace

