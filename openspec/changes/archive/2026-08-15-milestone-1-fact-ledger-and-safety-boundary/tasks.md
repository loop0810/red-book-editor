## 1. 跨端审核契约与版本指纹

- [x] 1.1 在服务端领域契约中增加 Fact Ledger、Claim Audit、support 状态、证据引用、audit/policy version 和 source/content digest 类型，并保持旧 JSONB 字段可选兼容
- [x] 1.2 在 Flutter `NoteDraft`、`ReviewResult`、`ReviewFinding` 和版本模型中增加审核快照解析、编码和 copyWith 支持
- [x] 1.3 实现 source 与草稿生成字段的规范化摘要和稳定 digest，定义审核快照与当前版本不匹配时的过期判定
- [x] 1.4 修改 `status_for_review` 与导出门禁，使缺少审计、过期审计、uncertain、warning 或 blocking 不能进入 `ready` 或绕过导出限制

## 2. Fact Ledger 与 Claim Audit

- [x] 2.1 实现从 `SourceExperience` 派生 Fact Ledger，覆盖月龄、场景、动作、观察、补充说明，并为事实记录 source path、类别和原始文本
- [x] 2.2 实现文本字段切分、中文规范化和来源证据匹配，区分可支持的事实表达、无法确认的解释和明显来源外声明
- [x] 2.3 实现 `ClaimAuditItem` 生成，覆盖选题角度、标题、正文、话题和封面文案，并限制声明、证据和原因摘要长度
- [x] 2.4 增加育儿领域确定性规则，识别诊断/用药、危险睡眠、产品绝对安全或发育功效、虚构经历、外部专家背书和保证性结论
- [x] 2.5 按风险策略合并 Fact Audit 与安全 findings：危险或关键虚构声明为 blocking，不确定概括为 warning/uncertain，并禁止无证据声明标记为 supported

## 3. 工作流、持久化与 API 接入

- [x] 3.1 将 Fact Ledger 和 Claim Audit 接入统一 `review_draft`，确保主生成、账号工作台生成、整篇重写、字段重生成和保存均使用同一审核入口
- [x] 3.2 保留 Agent final validator 的结构化输出和最低事实保留职责，避免将完整声明审核变成 Agent 无限修订循环
- [x] 3.3 在 `notes.review` 和草稿版本 JSONB 中保存审核快照，更新 repository、版本 DTO 和版本查询接口，并兼容历史版本缺失审核字段
- [x] 3.4 更新 API 响应和保存流程，确保审核快照随当前草稿返回，用户编辑后重新审核且不能复用旧 digest
- [x] 3.5 更新 Flutter 审核展示，显示声明支持状态、来源证据或命中文本，并保持现有 needs-review/blocking banner 行为

## 4. 自动化测试与回归评测

- [x] 4.1 增加 Fact Ledger 单元测试，覆盖 confirmed、observed、opinion、unknown、forbidden inference 和 source path
- [x] 4.2 增加 Claim Audit 单元测试，覆盖支持事实、未知药物/剂量、来源外宴会细节、产品功效、危险睡眠和虚构背书
- [x] 4.3 增加状态与导出门禁测试，覆盖缺少审计、过期审计、warning、uncertain、blocking 和通过审核
- [x] 4.4 增加主生成、重写、字段重生成、保存、重新打开和版本历史的集成测试，确认所有路径返回一致审核语义
- [x] 4.5 增加旧 JSONB 草稿兼容测试，确认缺少新字段时可以读取但不能静默成为 ready
- [x] 4.6 为五个脱敏 baseline 案例增加自动硬失败检查，记录事实阻断、安全阻断和运行失败，不覆盖已有 runs/scores

## 5. 契约、路线图与验证记录

- [x] 5.1 更新 `docs/contracts/CONTENT_WORKFLOW_CONTRACT.md`，记录 Fact Ledger、Claim Audit、digest 和状态/导出门禁语义
- [x] 5.2 更新 `docs/error/red-book-editor-agent-evolution-roadmap.md` 的当前状态、Milestone 1 勾选项和下一步，明确 P0-04/P1-03 仍未覆盖
- [x] 5.3 执行服务端格式化、类型检查、单元测试、集成测试和 baseline 自动检查，执行 Flutter format、analyze、根测试及相关 package tests
- [x] 5.4 运行 `openspec validate milestone-1-fact-ledger-and-safety-boundary --strict`，修复所有规格或任务一致性问题
- [x] 5.5 change 完成并归档后，向 `docs/error/change-fix-history.md` 追加实际改动、验证结果和未覆盖问题，不能只复制 proposal/tasks
