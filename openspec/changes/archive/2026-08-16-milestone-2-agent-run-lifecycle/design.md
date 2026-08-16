## Context

当前内容生成 API 在请求内同步执行 `ContentWorkflowService`，`AgentRuntime` 只返回内存中的 trace；数据库已有 `notes` 和草稿版本，但没有 AgentRun 或事件表。See proposal.md - Why。

实现必须继续遵守：领域代码不依赖 FastAPI/SQLAlchemy，数据库 schema 只通过 Alembic 演进，日志和运行事件不记录完整 prompt、用户正文、图片内容、token 或密钥，现有同步 API 和 Milestone 1 审核门禁保持兼容。

## Goals / Non-Goals

**Goals:**

- 用 PostgreSQL 保存 AgentRun 状态和有序安全事件，支持查询、SSE 断线续读和服务重启后的中断识别。
- 让 Runtime 通过可注入的取消检查和事件 sink 与应用层协作，而不引入编排框架。
- 用一个进程内 coordinator 启动后台任务，同时以数据库状态作为跨请求和重启后的权威事实。
- 为异步初始生成创建占位草稿；只有生成完成并通过统一审核后，才写入最终内容和可用状态。
- 为 Flutter 提供类型安全的运行状态/事件模型和取消、恢复调用，并在新建页面展示当前阶段。

**Non-Goals:**

- 不保存模型 messages、完整 prompt、用户正文副本或图片内容，也不实现真正按 token checkpoint 的断点续跑。
- 不改变现有同步 `/notes/generate`、`/notes/style`、`/notes/regenerate-field` 的响应格式。
- 不实现跨多进程/多副本的分布式 worker 锁；数据库唯一活动状态和进程内任务表只覆盖当前单实例开发部署。
- 不引入模型流式 token、自动发布、Memory、RAG 或 MCP。

## Decisions

### 1. AgentRun 使用独立表，事件使用 append-only 子表

新增 `agent_runs` 和 `agent_run_events`。运行表保存 `note_id`、operation、form、状态、阶段、attempt、cancel_requested、diagnostics/failure_code 和时间；事件表保存 run_id、sequence、event_type、phase、label、bounded summary 和 attempt，并对 `(run_id, sequence)` 建唯一约束。

选择事件表而不是把事件数组塞进 JSONB，是为了支持 `after_sequence` 游标查询、SSE 断线续读和每次事件独立提交。事件内容只使用 Runtime 已经压缩过的摘要，原始模型消息不进入 repository。

### 2. 占位 Note 作为恢复输入引用

异步初始生成创建一个只包含 SourceExperience、账号/栏目和 `style_form` 的占位 Note；AgentRun 只引用 `note_id`，不复制 prompt 或 source。成功后 worker 用统一审核结果更新该 Note，失败/取消则保留占位草稿并让状态保持 `needs_review`。恢复重新读取该 Note 的持久化输入，因此不依赖进程内 messages。

### 3. Coordinator 使用请求外任务和数据库轮询

`AgentRunCoordinator` 持有 `run_id -> asyncio.Task` 的短生命周期映射。创建/恢复接口只负责入队；worker 每次事件和状态变化使用独立 session 提交。取消接口先设置数据库 `cancel_requested`，再对当前实例 task 发出 cooperative cancel；Runtime 在模型/工具边界也检查数据库标记，避免只依赖内存 task。

应用启动时 coordinator 扫描 `running` 记录并标记 `interrupted`。这表示“可恢复的重新执行”，不是承诺从模型上下文中断点续跑；恢复时 attempt 加一，事件序号继续递增。

### 4. SSE 只读历史加轮询新事件

事件端点接受 `after` query 参数，并兼容 `Last-Event-ID`。先读取已有事件，再以短间隔查询新事件；遇到 completed/failed/cancelled/interrupted 终态后发送终态事件并结束。这样 TestClient、普通 HTTP 客户端和 Flutter 都能消费，不需要额外 broker。

### 5. 同步链路暂不强制改成异步

现有同步 API 继续按原语义直接返回 `StyledNoteResponse`，减少兼容风险。异步 API 复用同一个 `ContentWorkflowService` 和 styling Agent；一旦异步链路稳定，后续再决定是否让客户端主入口默认改用 AgentRun。

## Risks / Trade-offs

- [Risk] 单实例内存 task 表无法在多副本之间取消正在执行的网络请求 → 数据库取消标记仍然权威，Runtime 在每个边界检查；当前部署不宣称分布式 worker 保证。
- [Risk] worker 在模型调用期间无法立即观察取消 → 网关调用结束后立即检查，task cancel 作为当前进程的快速路径，并把结果持久化为 cancelled。
- [Risk] SSE 轮询会增加数据库读取 → 只读取递增游标，短连接在终态结束，并限制事件摘要和历史查询窗口。
- [Risk] 占位 Note 可能出现在草稿列表 → 用 `needs_review` 状态和运行 ID 标记，客户端可在列表中显示“生成中/可恢复”，后续可单独增加隐藏策略。
- [Risk] 恢复会重新调用模型并产生新结果 → attempt 和事件历史明确记录恢复，不把它描述为确定性的断点续跑。

## Migration Plan

1. 扩展领域 Runtime 的取消/事件端口，增加 AgentRun 领域 DTO 和 PostgreSQL migration。
2. 增加 repository、coordinator、生命周期扫描和 FastAPI AgentRun 路由。
3. 用 stub gateway 完成创建→事件→完成、取消、恢复和重启中断测试，再执行 PostgreSQL 集成测试。
4. 增加 Flutter 状态/事件模型、SSE 客户端和生成页阶段展示；旧同步 API 测试继续保留。
5. 若需回滚，停止使用异步 AgentRun 路由并保留新表；现有同步生成和旧客户端无需回滚。数据库回滚只通过 Alembic downgrade 执行。
