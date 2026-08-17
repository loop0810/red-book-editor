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
make run
```

`make run` 会将本机 Flutter 调试服务（`localhost`、`127.0.0.1` 和 `::1`）加入 `NO_PROXY`，避免终端代理拦截调试 WebSocket。若使用 `flutter run`，请先设置：

```sh
export NO_PROXY="localhost,127.0.0.1,::1"
export no_proxy="$NO_PROXY"
```

服务端：

```sh
cd server
uv sync
make run
```

安卓真机局域网调试：先在 Mac 上获取局域网 IP，并在可信局域网中启动服务端：

```sh
cd server
SERVER_HOST=0.0.0.0 make run
```

再从 `client/` 使用同一个 Mac IP 启动 Flutter：

```sh
flutter run -d <android-device> \
  --dart-define=API_BASE_URL=http://<mac-lan-ip>:8100
```

先确认真机浏览器可以打开
`http://<mac-lan-ip>:8100/health/live`。手机和 Mac 必须在可互通的局域网；不要把实际 IP 或密钥提交到仓库。

详细约束和验证命令见根 `AGENTS.md`、`docs/README.md`、`docs/client/README.md` 和 `docs/server/README.md`。
