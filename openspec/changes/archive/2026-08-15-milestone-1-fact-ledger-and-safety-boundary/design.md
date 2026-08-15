## Context

当前 `SourceExperienceDto` 是笔记事实来源，生成后的 `NoteDraftDto` 已包含 source 和 review，但 review 只保存 findings，`check_facts` 主要依赖文本包含判断。主生成、重写、字段重生成和保存已经有统一审核入口，适合在该入口增加来源声明审计，而不再为每个 Router 建立独立规则。

本 change 还需要兼容已有 JSONB 草稿、已有 Flutter 审核展示和当前离线 stub 测试。事实审计结果不能包含完整 prompt、模型消息或用户图片内容；只保存必要的来源引用、命中文本和风险原因。

## Goals / Non-Goals

**Goals:**

- 建立可确定重建的 Fact Ledger，并为事实保留来源路径。
- 对生成字段执行保守的 Claim Audit，区分 supported、uncertain 和 unsupported。
- 让审核快照与具体 source/content 版本绑定，防止过期审核结果被复用。
- 让医疗、危险睡眠、产品安全和虚构经历规则成为服务端 blocking/warning 门禁。
- 让 API、版本历史和 Flutter 能够读取并展示审核结果。
- 保持无真实模型时的可测试性，并让 baseline 案例可自动检查硬失败。

**Non-Goals:**

- 不引入向量数据库、互联网检索、图片理解或新的模型供应商。
- 不把模型返回的“supported”结论直接当作安全结论。
- 不实现 AgentRun、取消恢复、SSE、修订预算或工具预算。
- 不建立独立 Fact Ledger 数据库表；本阶段只保存审核快照。

## Decisions

### 1. 使用派生账本 + 审核快照，而不是新的事实存储

每次审核从 `SourceExperienceDto` 派生 Fact Ledger，事实项使用稳定的 source path，例如 `source.baby_month`、`source.actions[0]` 和 `source.observations`。账本本身不接受模型写入，也不作为另一份用户事实来源。

审核结果保存以下版本信息：

- source digest；
- content digest；
- policy/audit version；
- claim audit items 和 review findings。

这样可以在读取旧草稿时兼容缺失字段，并在 source 或生成字段改变后识别审核过期。选择 JSONB 快照而不是新表，是因为当前审核只需随笔记和版本恢复，不需要跨笔记查询事实；将来需要统计或检索时再单独设计 migration。

### 2. 采用保守的分层 Claim Audit

审核分为三层，按风险从确定性到语义判断排列：

```text
SourceExperience
    ↓
FactLedgerBuilder
    ↓
文本规范化与来源证据匹配
    ↓
育儿领域硬规则
    ↓
可选的模型辅助声明候选
    ↓
ClaimAudit + ReviewResult + NoteStatus
```

- 确定性层负责来源字段映射、月龄/动作/观察结果保留、药物与剂量、危险睡眠、绝对安全/疗效、虚构背书等硬规则。
- 对无法证明来源支持的声明采用 closed-world 策略：不能找到证据时最多标记为 `uncertain`，不能标记为 `supported`。
- 模型辅助只能提出声明候选、证据候选或 `uncertain` 建议；它不能降低确定性 blocking，也不能单独把声明提升为通过。
- 在 stub 和单元测试中使用确定性审计；真实模型复跑可以使用相同的审计接口，不把模型调用作为测试前置条件。

### 3. 扩展审核契约而不改变状态语义

服务端增加结构化类型：

- `SourceFact`：fact id、source path、kind、原始文本；
- `ClaimAuditItem`：字段、声明文本、support、evidence fact ids、reason、risk level；
- `ReviewResult`：保留 `passed` 和 `findings`，增加 claim audit、digest 和 policy version。

`passed` 继续表示没有 blocking，但 `status_for_review` 同时检查 warning、uncertain、缺失审计和 digest 不匹配，因此 `passed=true` 不能单独使草稿进入 `ready`。Flutter 继续使用现有审核 banner 和 finding 列表；新增字段只用于显示来源证据和声明状态，不新增编辑工作流。

### 4. 在共享审核入口完成所有路径接入

`review_draft` 负责构建账本、审计声明、合并领域安全规则并生成结果。已有 application service 的以下路径都调用它：

```text
主生成 / 账号工作台生成
整篇风格重写
字段重生成
用户保存
    ↓
统一 review_draft
    ↓
status_for_review + export gate
```

Agent final validator 继续负责 JSON 结构、表达形式和最低限度的来源事实保留；完整 Claim Audit 在生成结果进入业务草稿后执行，避免把所有审核问题变成 Agent 无限修订循环。

### 5. 用兼容方式保存当前审核和历史版本审核

当前笔记的审核快照继续写入 `notes.review`，版本 JSONB 同时保存该版本的 review snapshot；`DraftVersionDto` 增加可空 review 字段。旧记录没有这些字段时按“缺少审核”处理，读取仍成功，但状态不能被视为 `ready`，下一次保存或生成必须重新审核。

不新增数据库列或表，避免为一次性的审核结构引入不可逆 schema 变化；新增 JSONB 字段使用可选结构，以便旧数据平滑读取。

### 6. 用固定案例验证硬失败而不是把分数当作安全门禁

baseline runner 增加基于相同五个案例的自动硬失败检查，至少覆盖：

- 未知药物、剂量、医嘱和确定疗效；
- 产品绝对安全、促进发育或适合所有宝宝；
- 成人身上趴睡的可复制安全建议；
- 伪造研究、医生/专家背书和品牌绝对评价；
- 抓周、宴会、宝宝表现等来源外细节。

自动检查只负责标记回归结果，最终质量报告仍保留人工评分和人工修改稿。模型复跑产生的新 runs/scores 不覆盖已有基线。

## Risks / Trade-offs

- [Risk] 保守审计可能把自然的风格化表达判为 uncertain，增加 `needs_review` 比例 → 记录命中的字段和证据，先保障不可导出安全，再用 baseline 迭代规则减少误报。
- [Risk] 模型辅助审计可能给出错误的 supported 判断 → 代码层不允许模型覆盖确定性 blocking，也不允许无证据的 supported 进入 ready。
- [Risk] JSONB 审核快照会随 review 结构增长 → 限制 claim 数量、摘要长度和保存字段，不记录完整 prompt、模型响应或图片内容。
- [Risk] 旧草稿没有 digest 或 claim audit → 兼容解析但按缺少审核处理，下一次保存/生成时重算，不静默升级为 ready。
- [Risk] 生成、保存和版本恢复的审核字段不一致 → 在 service、repository、版本 API 和 Flutter model 增加同一组契约测试。

## Migration Plan

1. 先部署可选的 review/claim audit DTO 解析和确定性审核逻辑，保证旧 JSONB 可以读取。
2. 接入所有生成、保存和版本序列化路径；新写入记录开始包含 audit snapshot。
3. 执行服务端单元测试、API/集成测试和脱敏 baseline 自动检查。
4. 对现有旧草稿不做批量回填；用户下次保存、重生成或导出前触发缺少审核处理。
5. 如需回滚，保留旧字段读取逻辑，停止写入新 audit 字段，并继续把缺少审核的草稿置为 `needs_review`。
