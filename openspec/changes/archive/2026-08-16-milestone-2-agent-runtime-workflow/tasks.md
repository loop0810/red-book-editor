## 1. 运行状态与预算模型

- [x] 1.1 在领域运行时定义 Agent 阶段、完成/失败状态、稳定失败代码和运行计数器，并保持旧调用方可用
- [x] 1.2 扩展 Agent trace、成功结果和失败异常，支持阶段、当前阶段、步骤、修订、工具和重复错误诊断，同时不记录完整 prompt 或用户正文
- [x] 1.3 为运行配置增加总步骤、修订、工具调用、重复错误和阶段超时预算，并覆盖非法配置和默认值行为

## 2. 有限状态 Runtime

- [x] 2.1 为工具注册项增加服务端控制的阶段元数据，建立上下文收集、起草、批评、修订、审核和最终整理的合法转换
- [x] 2.2 实现独立的修订次数和工具调用次数计数，预算耗尽时返回稳定错误代码和部分 trace
- [x] 2.3 实现最终校验错误和工具错误的规范化、重复计数与熔断，区分重复错误和不同错误
- [x] 2.4 实现单阶段超时和总步骤保护，确保 timeout、预算耗尽和最终整理失败不会返回成功结果
- [x] 2.5 保持现有模型网关、白名单工具、结构化 validator 和旧 trace 字段兼容

## 3. 内容 Agent 接入

- [x] 3.1 将 styling Agent 的工具与最终 validator 接入阶段推进和新预算配置，保留现有事实校验与工具顺序
- [x] 3.2 在统一内容审核入口补充 `safety_review` 阶段诊断，不改变 Fact Ledger、Claim Audit、NoteStatus 或导出门禁语义
- [x] 3.3 确认主生成、整篇重写、字段重生成和保存路径继续复用同一运行控制与失败映射

## 4. 评测与回归测试

- [x] 4.1 增加 Runtime 单元测试，覆盖正常阶段、工具预算、修订预算、总步骤、阶段超时和非法配置
- [x] 4.2 增加重复错误测试，覆盖相同 validator 错误熔断、不同错误不误合并和敏感正文不进入 trace
- [x] 4.3 扩展 baseline runner 运行记录，保存阶段、计数器、预算耗尽类型、稳定失败代码和部分结果
- [x] 4.4 更新 Agent 评测 schema/校验和硬失败测试，保留历史 runs/scores 兼容且不覆盖旧记录
- [x] 4.5 增加 styling Agent、API 和集成回归测试，确认成功结果、失败 trace 与现有审核/导出语义一致

## 5. 验证与文档

- [x] 5.1 更新共享契约或运行诊断文档，明确新增字段、失败代码和旧客户端兼容行为
- [x] 5.2 执行服务端 lock-check、format-check、typecheck、unit、integration 和 eval-validate
- [x] 5.3 执行 Flutter format、analyze、根测试和 package tests，确认未引入客户端兼容性回归
- [x] 5.4 执行 `openspec validate milestone-2-agent-runtime-workflow --strict`，修复所有规格一致性问题
- [x] 5.5 完成 change 后更新 Agent 演进路线和 change-fix-history，记录实际覆盖范围、验证结果和未覆盖的持久化/流式能力
