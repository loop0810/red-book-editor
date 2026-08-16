# Change 修复记录

> 这是一份持续维护的实现记录，用来追踪 `docs/error/` 中的问题如何通过 OpenSpec change 被修复。
>
> 维护原则：问题文档记录“为什么要修”，OpenSpec change 记录“计划怎么修”，本文档记录“实际改了什么以及如何验证”。每个修复问题的 change 完成并归档前，都必须在本文档追加或更新对应记录。

## 维护约定

后续修复 `docs/error/` 中问题时，完成 OpenSpec change 的实现后同步以下内容：

1. 关联问题编号和来源文档，例如 `P0-01`、`P1-02`。
2. OpenSpec change 名称和归档位置。
3. 实际改动范围：服务端、客户端、契约、数据库、文档和测试。
4. 验证命令及结果；未完成或受环境限制的验证也要明确记录。
5. 尚未解决的相关问题，以及是否转入后续 change。

记录按完成时间倒序追加，不删除历史内容。若一个 change 只部分解决某个问题，应在“覆盖范围”中明确边界，避免把路线图中的计划误认为已经实现。

## 2026-08-16：harden-milestone3-regression-and-evaluation

### 关联问题

来源：[`red-book-editor-agent-evolution-roadmap.md`](./red-book-editor-agent-evolution-roadmap.md)

- Milestone 3 验证暴露的字段重生成集成断言过时、baseline 导入路径错误、嵌套结果被误判为 `fact_blocking`，以及 Agent 因最大步骤、修订预算和重复错误失败的问题。
- `P1-06`：评测尚未成为完整质量门禁；本次补强自动回归与可诊断失败记录，但不等同于人工质量评分或成本门禁。

OpenSpec：[`harden-milestone3-regression-and-evaluation`](../../openspec/changes/archive/2026-08-16-harden-milestone3-regression-and-evaluation/)

### 实际改动

- 服务端字段重生成集成测试改为断言目标字段 `FieldSuggestion`，并明确拒绝旧的整篇草稿字段；`make eval-baseline` 改用模块安全的 runner 入口。
- 自动硬失败检查支持嵌套 `FinalizeArgs` 结果和旧扁平草稿；事实覆盖按可独立识别的中文分句匹配，保留动作和安全边界；未解决校验问题时 `critique` 不得返回通过。
- 精确/趋势话题限制为主题相关候选，风格 profile 移除医疗背书、功效保证、品牌和平台结果等过于具体或不安全示例；新增对应单元回归测试。
- 修正 `ai-editing-interactions` Purpose，新增 `baseline-regression-gate` 主 spec，并同步 Agent runtime 与 Fact Ledger 主 spec。
- 根目录 `key.json` 已加入 `.gitignore`；本次未提交密钥，也未新增数据库 migration。客户端仅有既有测试文件格式化变更。

### 验证结果

- 服务端 lock-check、format-check、typecheck 通过；unit tests 为 71 passed、15 deselected；PostgreSQL integration tests 为 15 passed、71 deselected，测试后执行 `make migrate` 恢复到 Alembic head。
- `make eval-validate` 通过（5 个案例）；使用本地 `key.json` 仅注入进程环境执行同一五案例 baseline，`milestone3-fix-20260816-1215.json` 为 10/10 成功、0 个 Agent 失败、0 个自动硬失败；运行记录未保存 API key。
- Flutter format、`flutter analyze`、根测试和 package tests 通过（根测试 1 passed，package tests 31 passed）；`git diff --check` 通过。
- `openspec validate --all --strict` 通过（11 passed，0 failed）。
- `key.json` 已由 `.gitignore` 忽略，且未被 Git 跟踪。

### 覆盖范围与后续问题

- 本次 baseline 结果是自动状态、失败码和硬失败初筛，不包含人工评分、Token/成本统计或完整语义质量门禁；自动硬失败为零不能单独证明内容安全或质量。
- 图片理解、跨设备/关闭页面后的建议恢复、字符级富文本偏移和完整质量门禁仍属于后续工作；此前本地失败的旧 run JSON 保持未跟踪，不纳入本次提交。

## 2026-08-16：milestone-3-ai-native-editing

### 关联问题

来源：[`red-book-editor-agent-evolution-roadmap.md`](./red-book-editor-agent-evolution-roadmap.md)

- Milestone 3：编辑器无法比较 AI 修改、选择性采纳字段建议，且生成失败后的恢复体验不完整。

OpenSpec：[`milestone-3-ai-native-editing`](../../openspec/changes/archive/2026-08-16-milestone-3-ai-native-editing/)

### 实际改动

- 服务端新增目标字段 `FieldSuggestion` 契约、字段 digest、字段级审核 finding 和来源证据；字段重生成在内存中审核完整候选草稿，但 HTTP 只返回目标字段。
- Flutter `app_core` 增加建议会话模型、字段 Diff、冲突检测、SSE 游标重连和失败运行恢复；`note_creation` 增加候选预览、采纳/拒绝、冲突确认、审核字段定位和生成页继续运行/重试。
- 更新内容工作流契约、主 OpenSpec specs、Milestone 3 路线图和 `AGENTS.md` 的归档后自动提交约束；未新增数据库 migration。

### 验证结果

- 服务端 lock-check、format-check、typecheck、unit tests、eval validation 通过；unit tests 为 68 passed，integration-test 已执行但因本地 PostgreSQL 未启动而 15 项 skipped。
- Flutter format、analyze、根测试和全部 package tests 通过；package tests 共 31 项通过。
- `openspec validate milestone-3-ai-native-editing --strict` 通过，change 已归档并创建 Git commit。

### 未覆盖范围

- pending suggestion 仍只保留在当前编辑会话，不支持跨设备或关闭页面后的候选恢复。
- Diff 仍是字段级/句段级辅助展示，不承诺字符级富文本偏移；图片理解、Token/成本记录和更完整质量门禁留待后续 change。
- 集成测试需要可用 PostgreSQL 环境后再补跑。

## 2026-08-16：milestone-2-agent-run-lifecycle

### 关联问题

来源：[`red-book-editor-agent-evolution-roadmap.md`](./red-book-editor-agent-evolution-roadmap.md)

- `P1-03`：Trace 只能在请求完成后展示。

OpenSpec：[`milestone-2-agent-run-lifecycle`](../../openspec/changes/archive/2026-08-16-milestone-2-agent-run-lifecycle/)

### 变更目标

补齐 Milestone 2 第一片之后的 AgentRun 生命周期：让长耗时运行可持久化、查询、取消、恢复和通过 SSE 断线续读，同时保持同步生成 API、Fact Ledger、Claim Audit、草稿状态和导出门禁不变。

### 实际改动

#### 服务端运行生命周期

- 新增 `agent_runs`、`agent_run_events` 表和 Alembic migration，保存运行引用、状态、阶段、attempt、取消标记、诊断及递增事件序号。
- AgentRuntime 增加取消检查和安全事件 sink；新增单实例 coordinator，负责后台执行、状态更新、事件落库、取消、恢复和启动时将遗留 `running` 标记为 `interrupted`。
- 异步初始生成先创建占位 Note；只有统一生成与审核完成后才写入最终草稿。恢复重新读取持久化笔记输入，不保存模型 prompt、消息、用户正文或图片内容，也不宣称模型上下文 checkpoint。
- 新增创建/查询/取消/恢复 AgentRun API 和带 `after`/`Last-Event-ID` 游标的 SSE 事件端点。

#### Flutter 与共享契约

- app_core 增加 AgentRun、AgentRunDiagnostics、AgentRunEvent 模型，以及创建、查询、SSE、取消、恢复和进度生成 API。
- 新建笔记页面支持阶段摘要展示和取消按钮；旧同步生成回调继续兼容。
- 更新 [内容工作流契约](../contracts/CONTENT_WORKFLOW_CONTRACT.md)，明确 AgentRun 状态、事件、游标和隐私边界。

### 验证结果

- `server make lock-check`：通过。
- `server make format-check`：通过，58 个文件已格式化。
- `server make typecheck`：通过，58 个源文件无类型错误。
- `server make test`：62 passed，15 deselected，1 个既有 Starlette/httpx 弃用警告。
- 使用本机 PostgreSQL 执行 `DATABASE_URL=... make integration-test`：15 passed，62 deselected；覆盖 AgentRun 完成、SSE 游标、取消和恢复；测试后执行 `make migrate` 恢复到 Alembic head。
- `server make eval-validate`：5 个评测案例通过。
- Flutter format、`flutter analyze`、根测试和 package tests：通过（根测试 1 passed，package tests 20 passed）。
- `openspec validate milestone-2-agent-run-lifecycle --strict`：通过；delta 已同步到主 spec，change 已归档。

### 覆盖边界与后续问题

- 恢复是从持久化 Note 输入重新执行，不是 token 级模型 checkpoint；当前 coordinator 只保证单实例，未实现多副本分布式 worker 锁。
- SSE 传输阶段事件摘要，不传模型 token 流；图片理解、Diff/建议采纳、Token/成本记录和完整自动质量门禁仍属于后续迭代。
- 没有重新调用真实模型 baseline；重新运行需要 `DEEPSEEK_API_KEY`，因此没有新增人工评分结论。
- `make lint` 按当前迭代决定暂不处理，继续保留到正则/项目规则稳定后统一修复。

## 2026-08-16：milestone-2-agent-runtime-workflow

### 关联问题

来源：[`red-book-editor-agent-evolution-roadmap.md`](./red-book-editor-agent-evolution-roadmap.md)

- `P0-04`：Prompt 中的修订上限没有落实到代码。
- `P1-03`：Trace 只能在请求完成后展示（本次只补充运行诊断，不实现持久化和流式事件）。

OpenSpec：[`milestone-2-agent-runtime-workflow`](../../openspec/changes/archive/2026-08-16-milestone-2-agent-runtime-workflow/)

### 变更目标

把 Agent 从只有总步数保护的自由循环，推进为由服务端阶段、独立预算、超时和重复错误熔断控制的可诊断运行时；不改变 Milestone 1 的事实账本、安全审核、草稿状态和导出门禁。

### 实际改动

#### 服务端 Agent Runtime

- 增加 `collect_context`、`draft`、`critique`、`revise`、`safety_review`、`finalize` 阶段，以及 completed/failed/budget_exhausted 状态和稳定失败代码。
- 独立统计总步骤、修订、工具调用和重复错误，增加总步骤、工具调用、重复错误、修订和阶段超时保护。
- 工具注册项由服务端控制阶段推进；最终校验失败进入修订，统一审核入口记录 `safety_review` 阶段；失败保留截断 trace 和诊断信息，不返回可用成功结果。
- 主生成、整篇重写和字段重生成复用同一运行控制；不新增数据库表或 migration。

#### Flutter、契约与评测

- Agent trace 增加可选阶段字段，旧客户端忽略该字段仍可解析。
- Agent eval runner schema 升为 3，记录运行状态、最终阶段、计数器、失败代码和部分结果；历史 schema 1/2 保持可读。
- 增加 Runtime、styling Agent、API、评测诊断和集成回归测试，并更新内容工作流契约。

### 验证结果

- `server make lock-check`：通过。
- `server make format-check`：通过，53 个文件已格式化。
- `server make typecheck`：通过，53 个源文件无类型错误。
- `server make test`：61 passed，13 deselected，1 个既有 Starlette/httpx 弃用警告。
- 使用本机 PostgreSQL 执行 `DATABASE_URL=... make integration-test`：13 passed，61 deselected；测试后执行 `make migrate` 恢复到 Alembic head。
- `server make eval-validate`：5 个评测案例通过。
- Flutter format、`flutter analyze`、根测试和 package tests：通过（根测试 1 passed，package tests 19 passed）。
- `openspec validate milestone-2-agent-runtime-workflow --strict`：待本次文档收尾后执行。

### 覆盖边界与后续问题

- 本 change 第一片不实现 `AgentRun` 持久化、服务端重启后的恢复、取消/断点续跑、SSE/WebSocket，以及内部事件与客户端展示事件的拆分。
- 没有重新调用真实模型 baseline；重新运行需要 `DEEPSEEK_API_KEY`，因此没有新增人工评分、Token/成本数据或质量门禁结论。
- `make lint` 按当前迭代决定暂不处理；现有规则命中主要是中文标点/注释和 FastAPI 默认参数，后续正则与项目规则可能调整后再统一处理。


## 2026-08-15：milestone-1-fact-ledger-and-safety-boundary

### 关联问题

来源：[`red-book-editor-agent-evolution-roadmap.md`](./red-book-editor-agent-evolution-roadmap.md)

- `P0-03`：事实检查不能阻止新增事实。
- `P1-06`：当前评测尚未成为质量门禁（本次仅补充自动硬失败初筛，不等同于完整质量门禁）。

OpenSpec：[`milestone-1-fact-ledger-and-safety-boundary`](../../openspec/changes/archive/2026-08-15-milestone-1-fact-ledger-and-safety-boundary/)

### 变更目标

把用户来源、生成声明和育儿安全规则连接成一条可追溯的审核链路，使来源外经历、无法确认的结论和高风险安全表达不会静默进入 `ready` 或绕过导出门禁。

### 实际改动

#### 服务端事实审核与安全边界

- 在领域契约中增加 Fact Ledger、Claim Audit、`supported`/`uncertain`/`unsupported`、证据引用、审核版本和 source/content digest，并保持旧 JSONB 可选字段兼容。
- 从 `SourceExperience` 派生带 source path 的 confirmed、observed、opinion、unknown 和 forbidden inference 事实；模型生成内容不会写回事实账本。
- 对选题角度、标题、正文、话题和封面文案执行声明审计，使用保守的来源匹配，并将未知药物/医嘱、危险睡眠、产品安全、虚构经历、外部背书和保证性结论纳入安全规则。
- 将审核快照接入统一生成、重写、字段重生成、保存和版本恢复流程；旧或过期审核只能进入 `needs_review`，阻断风险不能导出。
- 在现有 `notes.review` 和版本 JSONB 中保存审核快照，不新增数据库表或 migration；服务端重新计算当前草稿状态，避免客户端伪造状态或复用旧 digest。

#### Flutter 与共享契约

- Flutter `NoteDraft`、`ReviewResult`、`ReviewFinding` 和版本模型支持审核快照编解码、`copyWith`、声明支持状态、证据和命中文本展示。
- 更新 [内容工作流契约](../contracts/CONTENT_WORKFLOW_CONTRACT.md)，明确审核版本、digest、状态和导出门禁语义。

#### Baseline 与文档

- baseline runner 为每条运行记录增加自动硬失败标签，覆盖 Agent 运行失败、事实阻断和安全阻断，并将 schema version 更新为 2；保留人工评分和既有 runs/scores，不覆盖历史资料。
- 更新路线图 Milestone 1 状态，明确 `P0-04`、`P1-03` 等后续能力仍未覆盖。
- 将 `content-safety-review` delta 同步到主 spec，并新增 `fact-ledger-and-claim-audit` 主 spec。

### 验证结果

- `server make lock-check`：通过。
- `server make format-check`：通过，52 个文件已格式化。
- `server make typecheck`：通过，52 个源文件无类型错误。
- `server make test`：50 passed，13 deselected。
- 使用本机 PostgreSQL 执行 `DATABASE_URL=... make integration-test`：13 passed，50 deselected。
- `server make eval-validate`：5 个脱敏案例通过；自动硬失败规则单元测试随服务端测试通过。
- Flutter format、`flutter analyze`、根测试及相关 package tests：通过（根测试 1 passed，package tests 19 passed）。
- `openspec validate milestone-1-fact-ledger-and-safety-boundary --strict`：通过；delta spec 已同步后 change 归档完成。
- `git diff --check`：通过。

### 覆盖边界与后续问题

- 本次没有重新调用真实模型 baseline；重新运行需要 `DEEPSEEK_API_KEY`，因此没有新增人工评分或质量门禁结论。
- `P0-04` 的独立修订/工具预算、重复错误检测和阶段超时仍未实现。
- `P1-03` 的 AgentRun 持久化、取消、恢复和流式事件仍未实现。
- `P1-04` 的素材理解，以及路线图中风格 YAML 具体背书/功效示例清理仍未覆盖。
- 本次不包含 Memory、RAG、MCP 或自动发布能力。

## 2026-08-15：milestone-0-reliable-generation-pipeline

### 关联问题

来源：[`red-book-editor-agent-evolution-roadmap.md`](./red-book-editor-agent-evolution-roadmap.md)

- `P0-01`：生成结果可能无法保存。
- `P0-02`：主要生成路径绕过最终审核。
- `P1-01`：字段重生成仍然生成整篇文案。
- `P1-02`：重新打开草稿后可能丢失表达形式。
- `P1-05`：账号上下文没有进入 Flutter 的主生成路径。

OpenSpec：[`milestone-0-reliable-generation-pipeline`](../../openspec/changes/archive/2026-08-15-milestone-0-reliable-generation-pipeline/)

### 变更目标

收敛主生成和账号工作台生成的服务端流程，使生成结果可以保存、列表查询和恢复；统一生成、重写、字段重生成和保存后的审核状态；让 `style_form` 在服务端、Flutter 和旧草稿兼容路径中保持一致。

### 实际改动

#### 服务端生成与持久化

- 新增内容工作流应用服务，统一账号/栏目上下文加载、生成、审核和状态计算。
- 主生成接口成功后创建 `NoteModel` 和第一条 `DraftVersionModel`，生成后的 `note_id` 可以直接保存。
- 账号工作台生成复用同一应用服务，校验账号隔离和启用栏目。
- repository 增加创建、保存和版本读取逻辑；`style_form` 写入现有 JSONB，旧草稿缺少该字段时仍可读取。
- 领域逻辑通过端口依赖上下文和持久化能力，不直接依赖 FastAPI 或 SQLAlchemy。

#### 审核、状态和导出门禁

- 集中映射审核结果：缺少审核、warning 或 blocking 均为 `needs_review`，只有无风险审核结果才为 `ready`。
- 主生成、账号工作台生成、整篇风格重写、字段重生成和保存都执行统一审核语义。
- 导出拒绝缺少审核结果和 blocking 风险，并返回可展示的风险原因；warning 保持 `needs_review`。
- 服务端不信任客户端提交的状态或审核结果来绕过状态计算。

#### 字段级重生成

- 为标题、正文、话题和封面文案增加单字段结构化结果及校验。
- 服务端只合并用户请求的目标字段，保留来源事实、其他字段、用户编辑和 `style_form`。
- 字段合并后对完整草稿重新审核。
- 旧草稿没有 `style_form` 且请求未提供表达形式时，返回明确的 `style_form_required`，不静默使用错误默认值。

#### Flutter 与跨端契约

- 服务端 DTO、保存/读取/版本接口和 Flutter `NoteDraft` 增加可空 `style_form`。
- 补齐 JSON 编解码、`copyWith`、保存请求和草稿恢复后的字段重生成。
- 编辑器和草稿列表展示审核提示及表达形式。

#### 测试与工具链

- 增加主生成→保存→列表→重新打开→版本历史集成测试。
- 增加主生成与账号工作台语义等价、字段保留、审核状态和导出门禁测试。
- 修正服务端 Makefile，使 `uv` 使用可写缓存，并通过当前解释器的 `python -m` 调用测试、类型检查和格式工具。
- 修正集成测试跨事件循环访问 asyncpg 连接池的问题。

### 验证结果

- 服务端 `make lock-check`：通过。
- 服务端 `make format-check`：通过，50 个文件已格式化。
- 服务端 `make typecheck`：通过，50 个源文件无类型错误。
- 服务端 `make test`：44 passed。
- 服务端 `DATABASE_URL=... make integration-test`：11 passed。
- Flutter format、analyze、根测试和相关 package tests：通过。

### 覆盖边界与后续问题

本 change 没有实现以下路线图能力，不能视为已经解决：

- `P0-03`：Fact Ledger、Claim Audit 和来源外事实的完整审计。
- `P0-04`：独立的修订次数、工具调用次数、重复错误检测和阶段预算。
- `P1-03`：持久化 AgentRun、取消、恢复和流式事件。
- `P1-04`：Agent 真正读取并使用图片素材。
- `P1-06`：自动评测质量门禁和完整可观测性。

这些问题后续若通过新的 OpenSpec change 修复，必须在本文档追加记录，并保留与对应 `docs/error/` 条目的关联。

## 2026-08-15：establish-agent-evaluation-baseline

### 关联问题

- `P1-06`：当前评测尚未成为质量门禁。
- 来源：[`red-book-editor-agent-evolution-roadmap.md`](./red-book-editor-agent-evolution-roadmap.md)
- OpenSpec：[`establish-agent-evaluation-baseline`](../../openspec/changes/establish-agent-evaluation-baseline/)

### 已完成改动

- 保留 5 个脱敏真实育儿案例和原有评分标准。
- 对已有 `deepseek-chat` 基线的 10 次输出完成逐条人工评分。
- 新增每次运行对应的分数、硬失败、失败原因和人工修订稿。
- 新增第一版 `baseline-report.md`，汇总平均分、硬失败数量、大幅重写比例和下一阶段问题。
- 记录出 `case-04` 两次 `agent_max_steps` 失败，以及重复 attempt 耗时异常短且内容一致的问题。
- 使用同一批案例完成新的 10 次真实模型复跑，失败运行保留了错误类型和 trace 摘要；新 run 与初始基线的可比性结论已写入报告。

### 当前边界

这次 change 建立了可复核的第一版基线和真实复跑流程，但还没有完成自动质量门禁，也没有对新复跑的 10 条输出重新进行完整人工评分。后续 Agent 或安全规则变更仍需复跑同一批案例，并根据需要新增对应 score 和对比结果。

## 后续记录模板

```markdown
## YYYY-MM-DD：<change-name>

### 关联问题

- `<问题编号>`：<问题标题>
- 来源：[`<error-doc>`](./<error-doc>)
- OpenSpec：[`<change-name>`](../../openspec/changes/archive/<date>-<change-name>/)

### 变更目标

<这次 change 要解决什么问题>

### 实际改动

- 服务端：
- Flutter：
- 契约/数据库：
- 测试/工具链：

### 验证结果

- `<command>`：<result>

### 覆盖边界与后续问题

- <尚未解决的问题>
```
