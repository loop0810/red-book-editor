## Why

安卓真机运行时，客户端的默认 API 地址 `127.0.0.1` 指向手机本身，无法访问运行在 Mac 上的 FastAPI 服务，导致启动阶段读取账号配置失败。现在需要支持通过 `--dart-define` 注入 Mac 的局域网地址，避免依赖 USB 端口转发或手工修改源码。

## What Changes

- 增加客户端 API 基地址的 `--dart-define=API_BASE_URL=...` 配置入口。
- 保留本地回环地址作为未配置时的默认值，兼容现有本机开发和测试。
- 为服务端开发启动命令增加可配置监听地址，允许局域网设备访问。
- 允许 Android debug/profile 构建访问开发环境的明文 HTTP 服务；生产构建不默认放开明文流量。
- 在客户端文档中补充 Mac 局域网调试步骤和连通性检查。

## Capabilities

### New Capabilities

- `client-runtime-configuration`: 定义客户端运行时 API 地址注入、默认值和非法配置行为。
- `lan-development-connectivity`: 定义开发服务监听局域网和 Android 调试构建访问 HTTP 服务的行为。

### Modified Capabilities

<!-- No existing capability requirements change. -->

## Impact

- Flutter 根应用、`app_core` API Client、Android debug/profile manifest 和客户端 README。
- Python 服务端 Makefile 的开发启动参数及服务端 README。
- 新增客户端 API 地址解析测试、服务端启动配置检查和必要的 Flutter 验证。
