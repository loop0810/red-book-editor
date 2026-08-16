## Context

Milestone 3 已将字段重生成响应改为目标字段 `FieldSuggestion`，但旧集成测试仍按完整草稿断言。真实 baseline 的最终结果包裹在 `draft` 字段内，而自动硬失败检查只读取外层字段，导致成功结果被全部误标为事实失败。与此同时，风格 Agent 的 critique 使用严格整句匹配，且可能在仍有 issue 时返回 `passed=true`，造成模型在 critique、finalize 和最终校验之间重复消耗预算。

本 change 不新增数据库表，不改变已发布的字段建议 HTTP 响应契约，也不保存模型密钥、完整 prompt、用户正文或图片内容。

## Goals / Non-Goals

**Goals:**

- 让 Milestone 3 集成测试断言当前 `FieldSuggestion` 契约。
- 让 `make eval-baseline` 从 `server/` 根目录可直接运行。
- 修正 baseline 自动初筛读取嵌套结果的错误，并保留失败诊断。
- 让事实覆盖校验支持安全分句改写，降低无效修订循环。
- 让 critique 的 `passed` 与最终校验前置条件一致。
- 清理风格档案中会诱导虚构医疗背书、疗效、品牌或宴会细节的示例。
- 将本地根目录 `key.json` 加入 Git 忽略。

**Non-Goals:**

- 不把自动硬失败初筛升级为完整语义模型审核。
- 不保证本次 baseline 所有案例无事实或安全风险；风险输出仍应被记录并进入人工复核。
- 不调整 Agent 的总体预算数值来掩盖失败，也不引入新的模型供应商或依赖。
- 不删除已有 baseline 运行记录，不提交 `key.json`。

## Decisions

### 1. 以实际输出包结构为准兼容硬失败检查

`run_agent_eval.py` 保存的 `draft` 是 `FinalizeArgs` 结构，业务草稿位于 `draft.draft`；旧测试和 stub 记录可能仍传入扁平草稿。硬失败检查先解包一层，统一提取可编辑字段，再执行现有正则和来源场景检查。这样修复误报而不改变硬失败规则本身。

### 2. 将来源事实拆成可识别分句

事实校验对 scenario、observation 等包含中文逗号的来源字段拆分为事实单元，逐单元执行紧凑化匹配，并保留“去除常见助词”的兼容逻辑。动作字段默认作为一个单元，避免把复杂动作拆得过细。来源外声明仍由 Claim Audit 和安全规则处理，因此“允许改写”不等于“允许新增事实”。

### 3. critique 只有在没有待处理 issue 时才能通过

`critique_draft` 的 `passed` 使用同一组 `issues` 作为前置条件；只要存在事实、禁用表达、话题数量或富文本问题，就返回 `false`。这会让 Agent 在 finalize 前看到真实反馈，减少“critique 通过、最终校验失败”的循环。预算仍保持现有值，预算耗尽时继续返回稳定诊断。

### 4. 通过风格档案和标签选择降低错误诱因

移除具体医生、医院、药物疗效、平台审核结果、品牌和安全保证示例；`suggest_tags` 只保留通用标签及与主题匹配的精准/趋势标签，避免把无关医疗标签注入广告或育儿经历。风格规则仍由版本化 YAML 加载，不增加外部检索。

### 5. 保持本地密钥与评测记录分离

在根 `.gitignore` 增加 `key.json`。现有运行记录不删除，验证命令只读取环境中的 key，不打印 key 内容。最终检查确认 key 未进入 staged 或 tracked 文件。

## Risks / Trade-offs

- [Risk] 分句匹配可能接受过于宽泛的短语 → 只拆分带明确标点的事实字段，保留完整动作匹配，并继续运行来源外声明和安全审核。
- [Risk] critique 更严格后某些模型运行更容易预算失败 → 失败会更早、更准确地暴露；通过清理 profile、修正标签和减少重复反馈降低该风险。
- [Risk] 自动硬失败仍可能漏掉复杂语义虚构 → 明确保留其“初筛”定位，baseline 继续要求人工评分和人工修改稿。
- [Risk] 忽略规则可能覆盖其他目录的 `key.json` → 这是有意的安全默认，任何本地同名密钥都不应进入仓库。

## Migration Plan

1. 更新 OpenSpec 主 Purpose、delta specs、字段建议集成测试和 baseline 单元测试。
2. 修正 Makefile、硬失败检查、事实匹配、critique、标签选择和风格 YAML。
3. 执行服务端单元/集成测试、baseline 校验、OpenSpec strict validation 和 Flutter 回归测试。
4. 使用本地 key 重新运行同一批脱敏案例，新增独立 run 记录并汇总状态、失败码和硬失败标签。
5. 确认数据库恢复到 Alembic head，确认 `key.json` 和本地运行记录未被提交。

回滚时可恢复旧测试/配置行为；不需要数据库迁移或数据回滚。
