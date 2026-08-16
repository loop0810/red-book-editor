## 1. Domain runtime cancellation and events

- [x] 1.1 增加 AgentRun 生命周期状态、取消失败代码、运行事件和安全摘要契约
- [x] 1.2 扩展 AgentRuntime 的取消检查与异步事件 sink，覆盖模型、工具、阶段和终态事件
- [x] 1.3 增加 Runtime 单元测试，确认取消不会成功返回、事件有序且摘要有界

## 2. Persistence and migration

- [x] 2.1 增加 AgentRun、AgentRunEvent SQLAlchemy 模型和 repository 端口映射
- [x] 2.2 创建 Alembic migration，增加状态/事件索引与 `(run_id, sequence)` 唯一约束
- [x] 2.3 增加 PostgreSQL repository 测试，覆盖状态更新、游标读取、取消标记和 attempt 递增

## 3. Run coordinator and workflow integration

- [x] 3.1 实现单实例 AgentRun coordinator，支持入队、后台执行、任务注册和幂等启动
- [x] 3.2 创建异步初始生成的占位 Note，worker 完成后复用统一审核和 Note 持久化语义
- [x] 3.3 实现取消、失败、完成、恢复和启动时 orphaned running 扫描，保留事件历史
- [x] 3.4 增加 coordinator 单元测试，覆盖成功、模型失败、取消、重复恢复和重启中断

## 4. AgentRun HTTP and SSE API

- [x] 4.1 增加创建运行、查询状态、取消和恢复的请求/响应 DTO 与路由
- [x] 4.2 增加带 `after`/`Last-Event-ID` 游标的 SSE 事件端点，终态后关闭流
- [x] 4.3 增加 API 测试，覆盖状态码、账号隔离、事件顺序、断线续读和终态行为
- [x] 4.4 更新服务端内容工作流契约，明确 AgentRun API、事件类型和隐私边界

## 5. Flutter client and progress UI

- [x] 5.1 增加 AgentRun/AgentRunEvent 跨端模型和 JSON 兼容解析
- [x] 5.2 增加 API Client 的创建、查询、SSE 订阅、取消和恢复方法
- [x] 5.3 在新建页面增加可选的 AgentRun 生成路径，展示当前阶段、事件摘要、取消和重试入口
- [x] 5.4 增加 app_core 与 note_creation 测试，保留旧同步生成调用兼容

## 6. Verification and documentation

- [x] 6.1 执行服务端 lock-check、format-check、typecheck、unit、integration 和 eval-validate
- [x] 6.2 执行 Flutter format、analyze、根测试和 package tests
- [x] 6.3 严格校验 OpenSpec，更新 Agent 演进路线和 change-fix-history，明确恢复不是模型 checkpoint
- [x] 6.4 同步主 specs 后归档 change，确认 PostgreSQL 容器保持运行且数据库在 Alembic head
