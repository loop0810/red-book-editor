## 1. 跨端契约与审核状态

- [x] 1.1 在 `docs/contracts/CONTENT_WORKFLOW_CONTRACT.md` 更新生成、局部重生成、审核状态和导出门禁语义，移除“风格化路径不触发阻断级检查”的过期约束
- [x] 1.2 为服务端 `NoteDraftDto`、生成响应、更新请求和字段重生成请求增加可空 `style_form`，并保持旧草稿缺少该字段时可读取
- [x] 1.3 为 Flutter `NoteDraft` 增加 `styleForm`，补齐 JSON 编解码、`copyWith`、生成/保存/重生成请求和恢复逻辑
- [x] 1.4 增加集中式审核状态映射，确保缺少审核、warning、blocking 和无风险结果分别得到一致的草稿状态

## 2. 共享生成与持久化服务

- [x] 2.1 定义内容工作流应用服务需要的账号/栏目上下文和笔记持久化端口，保持领域逻辑不直接依赖 FastAPI 或 SQLAlchemy
- [x] 2.2 将账号和栏目校验、上下文加载、生成、审核和状态计算迁移到共享应用服务
- [x] 2.3 让 `/api/v1/notes/generate` 调用共享服务并在成功后创建 `NoteModel` 与第一条 `DraftVersionModel`
- [x] 2.4 让 `/api/v1/accounts/{account_id}/notes` 复用同一生成服务，保留账号隔离和栏目有效性校验
- [x] 2.5 让 `/api/v1/notes/style`、保存草稿和所有生成失败路径复用同一审核和状态语义
- [x] 2.6 更新服务端 `note_dto`、repository 和版本读取映射，完整保存和返回 `style_form`

## 3. 字段级重生成

- [x] 3.1 为标题、正文、话题和封面文案分别定义单字段结构化结果及服务端校验
- [x] 3.2 实现字段级生成流程，使用草稿保存的 `style_form` 作为未显式传入 `form` 时的默认上下文
- [x] 3.3 将字段结果服务端合并回原草稿，确保来源事实、其他字段、表达形式和用户编辑不被覆盖
- [x] 3.4 对字段合并后的完整草稿重新执行审核，并处理旧草稿缺少 `style_form` 时的 `style_form_required` 错误

## 4. 导出门禁与 API 行为

- [x] 4.1 修改导出接口：审核结果缺失或 blocking 风险不得导出，并返回可展示的风险原因
- [x] 4.2 确保 warning 草稿保持 `needs_review` 和审核提示，不得被任一生成或保存路径静默改成 `ready`
- [x] 4.3 确保服务端不信任客户端提交的 `status`、`review` 或 `style_form` 来绕过审核状态计算
- [x] 4.4 更新 Flutter 编辑器和草稿列表，使恢复后的表达形式继续用于字段重生成，并正确展示审核状态

## 5. 回归测试

- [x] 5.1 增加主生成接口生成→保存→列表→重新打开→版本历史的服务端集成测试
- [x] 5.2 增加账号工作台生成接口与主生成接口的上下文、审核和持久化语义等价性测试
- [x] 5.3 增加真实模型路径、stub 路径、整篇重写、字段重生成和保存后的审核状态测试
- [x] 5.4 增加缺少审核、blocking、warning、无风险和导出门禁的 API 测试
- [x] 5.5 增加字段重生成只改变目标字段、保留 `style_form` 和保留用户编辑的测试
- [x] 5.6 增加 Flutter `NoteDraft` 的 `style_form` JSON 往返、保存请求和恢复后重生成测试
- [x] 5.7 执行服务端格式检查、类型检查、单元/API/集成测试，以及 Flutter format、analyze 和相关 package tests
