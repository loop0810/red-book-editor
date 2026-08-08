## Why

当前工作台生成的文案是中性甚至模板化的内容，与小红书流行风格差距很大；同时项目的首要目标是实践 agent 开发，理解 agent 的工作原理。这个变更将手写一个最小的 agent 运行时，并把它用于实现育儿笔记的小红书风格转换，让"学 agent"和"内容像小红书"两个目标同时落地。

## What Changes

- 接入真实模型：在现有可插拔端口后实现 DeepSeek 适配器（`deepseek-chat`），API key 通过服务端环境变量注入，不落仓库、不进客户端、不记录日志。
- 手写最小 agent 运行时：消息与工具调用循环、最大步数、结构化输出校验、超时重试、逐步 trace 记录。不引入 agent 框架，先理解底层机制。
- 新增育儿风格转换 agent：内置三个表达形式的风格档案（科普 / 经验 / 软文），以版本化 YAML 文件存放在服务端代码库；agent 按"读取档案 → 规划结构 → 写作 → 自评 → 修订 → 输出"循环工作。
- 风格转换工具集：`load_style_profile`（读档案）、`suggest_tags`（三层标签）、`critique_draft`（对照档案自评，含事实保持核对）、`finalize_note`（输出结构化草稿）。
- 富文本装饰：emoji/分隔符号规则、三层话题标签（泛标签 + 精准标签 + 蹭热点标签）、封面文案与 CTA 模式，由规则为主、模型辅助生成。
- 新增风格转换 API：将已生成草稿按指定表达形式重写，响应包含风格化后的 `NoteDraft` 和 `AgentTrace`（agent 每一步的思考与工具调用过程）。
- 客户端展示：新建笔记时选择表达形式（科普 / 经验 / 软文），风格化完成后展示每一步 agent 轨迹，便于用户理解和校验。
- 账号工作台调整：栏目预设调整为三种表达形式；账号定位文案覆盖备孕 → 孕检 → 育儿全程（V1 不动年龄字段 schema）。
- 安全边界声明：**V1 风格转换路径不触发阻断级内容检查**（育儿风格常见的"就医红线""专家背书"等写法与现有阻断规则冲突），检查能力保留，后续版本再定义分级规则。

## Capabilities

### New Capabilities

- `agent-runtime`: 模型网关（DeepSeek 适配器）、手写 agent 循环、工具协议、结构化输出处理、trace 记录与错误语义。
- `note-styling`: 小红书风格档案（YAML）、风格转换 agent（规划 → 写作 → 自评 → 修订）、富文本装饰规则、风格化结果与 trace 输出。

### Modified Capabilities

- `note-creation`: 新建笔记增加表达形式选择；生成流程产出风格化草稿并附带 agent trace；V1 风格化路径不再由阻断检查决定草稿状态。
- `account-workspace`: 栏目从主题预设调整为三种表达形式预设（科普 / 经验 / 软文）；账号定位覆盖备孕-孕检-育儿阶段。
- `content-safety-review`: V1 明确"风格转换路径不调用阻断检查"，安全边界后置为范围外决策。

## Impact

- `server/`：新增领域端口（模型网关、agent 运行时、工具协议）、DeepSeek 基础设施适配器、`content_workflow` 下 agent 模块、三份风格档案 YAML、环境配置（`DEEPSEEK_API_KEY` 等）、单元与集成测试。
- `client/`：`app_core` 新增风格形式、agent trace、风格化响应的模型与 API 客户端；`note_creation` 增加表达形式选择与 trace 展示；`account_workspace` 更新栏目预设。
- `docs/contracts/`：新增风格转换端点、`StyleForm`、`AgentTrace`、错误与重试语义。
- 运维：用户需要提供 DeepSeek API key（服务端环境变量）；无数据库 schema 变更，风格档案不进数据库。
- 非目标：不做多领域（仅育儿）、不做发布数据回流与记忆（后续阶段）、不引入 agent 框架、不自动发布、风格档案 V1 不支持客户端在线编辑。
