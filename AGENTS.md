# Red Book Editor Monorepo 约束

## 任务范围

- `client/` 维护 Flutter 客户端和 Dart packages。
- `server/` 维护 Python/FastAPI 模块化单体。
- `docs/contracts/` 是客户端与服务端共享请求、响应、状态和错误语义的权威位置。
- 根 `openspec/` 是跨端变更的规划入口。
- 修改产品行为、跨端 API、数据 schema、安全边界或模块边界前，先更新当前 OpenSpec change。

## 修改纪律

- 开始工作前检查目标目录和未提交修改，保留无关用户变更。
- 不提交密钥、签名材料、构建目录、本地环境绝对路径或真实宝宝照片。
- 客户端不直接调用模型供应商，不包含模型密钥。
- 服务端不记录模型密钥、访问令牌、用户笔记正文或图片内容。
- 数据库 schema 只能通过 Alembic migration 演进。
- 领域逻辑不得直接依赖 FastAPI、SQLAlchemy 或具体模型 SDK。

## Change 修复记录

- 完成并归档修复 `docs/error/` 问题的 OpenSpec change 后，必须同步更新 `docs/error/change-fix-history.md`。
- 记录必须包含关联问题、change 名称、实际改动、验证结果和未覆盖范围；不能只复制 proposal 或 tasks。
- OpenSpec change 完成归档后，必须自动创建 Git commit；commit 只包含本次 change 及其归档、文档同步和验证记录相关文件，不自动 push 到远程。

## 验证

客户端：

```sh
cd client
dart format --output=none --set-exit-if-changed .
flutter analyze
flutter test
flutter test packages/*/test
```

服务端：

```sh
cd server
make lock-check
make format-check
make typecheck
make test
make integration-test
```
