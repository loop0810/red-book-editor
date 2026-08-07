# Red Book Editor

小红书育儿内容工作台 monorepo，包含 Flutter 移动客户端和 Python 服务端。

## 项目结构

- `client/`：Flutter iOS/Android 客户端及 Dart workspace
- `server/`：Python/FastAPI 模块化单体、数据库迁移和服务端测试
- `docs/`：产品、跨端契约、客户端、服务端、决策和学习记录
- `openspec/`：变更规划和规格

## 当前范围

第一版围绕单一 0～2 岁育儿账号，生成、编辑和保存小红书笔记，并由用户手动复制发布。服务端负责内容工作流和安全检查，客户端不保存模型密钥、不自动发布到小红书。

## 开发入口

客户端：

```sh
cd client
flutter pub get
flutter run
```

服务端：

```sh
cd server
uv sync
make run
```

详细约束和验证命令见根 `AGENTS.md`、`docs/README.md`、`docs/client/README.md` 和 `docs/server/README.md`。
