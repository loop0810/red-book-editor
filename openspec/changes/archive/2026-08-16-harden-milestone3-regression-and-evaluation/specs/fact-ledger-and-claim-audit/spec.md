## ADDED Requirements

### Requirement: Accept safe paraphrases while preserving source coverage

来源事实校验 SHALL 将可独立识别的事实分句作为覆盖单元，允许自然语言中的语气、助词和标点变化；校验 MUST 继续要求关键事实单元被表达，并不得因此放宽来源外声明、安全结论或未知结果的审核。

#### Scenario: Accept a natural Chinese paraphrase

- **WHEN** 来源事实为“宝宝喜欢爬来爬去，开始想要往沙发上爬”，生成正文分别表达“宝宝喜欢爬来爬去”和“开始想要往沙发上爬了”
- **THEN** 事实覆盖校验通过，不要求整句逐字连续出现

#### Scenario: Keep an unsupported product result blocked

- **WHEN** 来源只说明购买了软包楼梯和宝宝喜欢，但生成内容声称产品“绝对安全”或“一定促进发育”
- **THEN** 声明审核仍标记安全/事实硬失败，不能因为其他事实单元已覆盖而放行
