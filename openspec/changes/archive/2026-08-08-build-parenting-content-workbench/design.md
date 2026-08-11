## Context

仓库当前只有 OpenSpec 配置，没有既有应用架构。参考 `/Users/loop/Desktop/My Work/Kitchen` 的 monorepo 组织方式，本项目需要从零建立 Flutter 客户端和 Python 服务端，同时保持客户端、服务端、共享契约和长期文档边界清晰。V1 只服务一个账号、一个 0～2 岁育儿方向，并通过人工复制完成小红书发布。需求细节见 proposal.md 和各能力规格。

## Goals / Non-Goals

**Goals:**

- 用 Flutter 提供 iOS 与 Android 的统一移动端体验。
- 用 Python 服务端承载 Agent 工作流、模型调用、内容检查和持久化。
- 用结构化的账号和栏目上下文驱动内容生成。
- 保留用户真实经历作为事实来源，支持可追溯的草稿版本。
- 将生成、编辑、安全检查、素材管理和手动发布记录串成一个跨端工作流。
- 采用可扩展的 monorepo 和模块边界，为未来增加账号、领域和矩阵数据做准备。

**Non-Goals:**

- 不把 Agent 核心逻辑、模型密钥或安全规则放在 Flutter 客户端。
- 不实现小红书自动登录、自动发布、点赞、评论或数据抓取。
- 不做医疗问答、疾病诊断、用药推荐或儿童发育评估。
- 不在 V1 依赖 AI 图片生成；先支持用户图片和封面/配图建议。
- 不实现多用户协作、复杂权限和商业化计费。

## Decisions

### 1. 采用 monorepo 管理 Flutter 客户端和 Python 服务端

项目根目录负责 OpenSpec、AGENTS 和长期文档；`client/` 负责 Flutter 应用及 Dart packages；`server/` 负责 Python 服务端；`docs/` 按 product、contracts、client、server、decisions 和 learning 分区。这个结构参考 Kitchen，便于跨端变更在同一个仓库中规划、实现和验证。

目标结构如下：

```text
red_book_editor/
├── client/
│   ├── lib/
│   ├── packages/
│   │   ├── app_core/
│   │   ├── design_system/
│   │   ├── account_workspace/
│   │   ├── note_creation/
│   │   ├── asset_library/
│   │   └── publish_records/
│   └── test/
├── server/
│   ├── src/red_book_editor_server/
│   │   ├── app/
│   │   ├── domain/
│   │   ├── infrastructure/
│   │   └── modules/
│   ├── tests/
│   ├── migrations/
│   ├── pyproject.toml
│   └── Makefile
├── docs/
├── openspec/
└── AGENTS.md
```

### 2. Flutter 只负责客户端体验，Agent 放在 Python 服务端

Flutter 负责账号配置、经历输入、笔记编辑、图片选择、草稿查看、复制和发布记录。服务端负责结构化经历、选题、正文生成、安全检查、数据库、文件存储和模型调用。客户端通过 HTTPS API 获取结构化结果。

替代方案：在 Flutter 内直接调用模型或运行完整 Agent。该方案会暴露密钥、难以统一更新提示词和安全规则，也不利于多设备与多账号扩展，因此不采用。

### 3. 客户端按功能拆分 Dart packages

根 Flutter App 只负责路由、依赖装配和跨功能协调；账号、笔记、素材和发布记录分别放在 feature package 中；共享状态、设计系统和基础网络能力放入 core package。Feature 之间不直接依赖，通过类型化模型、UseCase、Repository 和 Riverpod 等边界通信。

### 4. 服务端采用 Python 模块化单体

按 Kitchen 的 Python 服务端方向，使用 Python、FastAPI、SQLAlchemy、Alembic 和 PostgreSQL。`app` 负责 FastAPI 装配、路由和依赖；`domain` 保存稳定的领域端口和模型；`infrastructure` 实现数据库、模型客户端和文件存储适配器；`modules` 按账号、笔记、审核和发布记录组织业务。

业务 handler 不直接创建数据库连接或外部模型客户端，统一通过依赖和领域端口访问基础设施。V1 不拆分微服务。

### 5. Agent 采用结构化工作流，而不是多 Agent 自由对话

用户输入先整理为 `SourceExperience`，再由选题、标题、正文和检查步骤分别消费。服务端使用结构化 JSON schema 约束模型输出，并把模型结果转换为 API DTO。解析失败时保留原始输入并允许重试。

```text
SourceExperience
    ↓
Experience Structurer
    ↓
Topic / Title Generator
    ↓
Note Generator
    ↓
Safety Reviewer
    ↓
Draft Response
```

这样可以减少模型补写未发生经历，也支持只重新生成一个字段而不覆盖其他内容。

### 6. 跨端契约集中管理

客户端和服务端共同依赖的请求、响应、标识符、错误、风险等级和状态语义记录在 `docs/contracts/`。API 变更先更新契约，再分别更新 Python DTO、Flutter model 和测试。服务端内部实现细节不复制到客户端文档。

### 7. 安全检查分为阻断级和提示级

检查器输出结构化结果：风险等级、命中内容、原因和建议操作。疾病判断、用药方案、虚构经历和保证性医疗效果属于阻断级；普通表达优化和轻微定位偏差属于提示级。对外笔记不自动添加固定免责声明，检查结果只在工作台中展示。

### 8. 图片先采用服务端存储和移动端上传导出

移动端选择图片后上传到服务端的账号范围存储，服务端返回受控的素材标识；编辑器支持预览、排序和导出。图片生成服务作为后续可插拔能力，不阻塞第一版文字工作流。

### 9. 使用适配层隔离模型和存储供应商

业务层只依赖内容生成、内容审核和文件存储的领域接口，不直接耦合具体模型供应商、对象存储或 SDK。V1 可先使用本地开发存储和一个模型适配器，生产配置通过环境变量注入，禁止提交密钥。

## Risks / Trade-offs

- [Risk] Flutter 与 Python API 的契约漂移 → 在 `docs/contracts/` 定义共享语义，并为每个跨端能力增加 API 契约测试。
- [Risk] 模型可能把个人经历扩写成未发生事实 → 强制保留 `SourceExperience`，要求关键陈述可追溯，并对 unsupported claim 做检查。
- [Risk] 医疗相关内容边界判断不稳定 → 使用规则检查与模型检查结合；阻断级结果必须人工修改或放弃，不自动放行。
- [Risk] 宝宝照片属于敏感的家庭素材 → V1 限制在账号范围内访问，避免公开 URL，明确删除行为，并为后续加密存储预留接口。
- [Risk] 生成内容看起来模板化 → 让用户先提供真实场景和做法，支持栏目模板和局部重写，而不是只根据一个主题生成整篇文章。
- [Risk] 移动端网络失败导致用户丢失输入 → Flutter 在请求前保留本地草稿状态，服务端失败时允许重试，不清空用户输入。
- [Risk] monorepo 初期边界过度拆分 → 只拆分有独立职责和测试边界的 feature package，避免为单个页面创建 package。

## Migration Plan

这是空仓库的新应用，不涉及旧数据迁移。初始阶段先创建 monorepo 目录、Flutter workspace 和 Python 服务端运行时，再按 API 契约接入业务模块。数据库使用 Alembic migration 作为 schema 唯一演进入口；素材存储通过抽象接口保留从本地开发目录迁移到对象存储的路径。

如果后续模型、存储或账号数量扩展，按版本迁移数据库 schema，客户端保留草稿导出能力作为服务端不可用时的回退手段。

## Open Questions

- 具体模型供应商和提示词版本可在接入时选择，只要满足结构化输出和安全检查契约。
- 生产环境对象存储和部署平台可在基础工作流跑通后单独确定，不改变 Flutter + Python 服务端边界。
