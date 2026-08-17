## Context

当前 `app_core` API Client 将 `127.0.0.1:8100` 写死，真机上的回环地址不会指向 Mac。服务端的开发启动命令也使用 Uvicorn 默认的回环监听。Android manifest 目前仅声明网络权限，未区分开发和生产传输策略。

## Goals / Non-Goals

**Goals:**

- 在编译期注入客户端 API 基地址，并保留测试可覆盖的构造参数。
- 让服务端的开发启动入口可通过环境变量开放到局域网。
- 仅对 Android debug/profile 放行本地 HTTP，避免影响 release 的生产传输边界。
- 提供可复制的真机局域网启动文档。

**Non-Goals:**

- 不新增运行时配置页面或远程配置服务。
- 不把具体 Mac IP、模型密钥或其他本地环境值提交到仓库。
- 不改变服务端 API 路径、账号数据模型或生产部署方式。

## Decisions

- **Dart define 作为客户端配置入口。** 使用 `String.fromEnvironment` 读取 `API_BASE_URL`，因为地址在 `flutter run`/构建时已确定，不需要运行时存储或网络发现。API Client 保留显式 `baseUrl` 构造参数，供测试和特殊调用覆盖。未配置时继续使用当前回环默认值。
- **统一去除基地址末尾斜杠。** 请求路径目前通过字符串拼接生成；在边界处规范化一次，比逐个请求处理重复斜杠更小且不会改变路径契约。
- **服务端以 `SERVER_HOST` 控制监听。** 将 host 纳入现有 Settings，并让 Makefile 和模块入口使用同一配置。默认仍是回环地址；局域网调试时显式使用 `SERVER_HOST=0.0.0.0`，避免默认扩大服务暴露范围。
- **开发变体单独允许明文 HTTP。** 在 debug/profile manifest 添加 `usesCleartextTraffic`，不修改 main/release manifest。这样局域网调试可以继续使用 HTTP，而 release 不会因调试便利配置而放宽传输要求。
- **文档同时记录两端命令。** 客户端使用 `--dart-define=API_BASE_URL=...`，服务端使用 `SERVER_HOST=0.0.0.0`；文档要求先用 `/health/live` 验证连通性，再启动 Flutter。

## Risks / Trade-offs

- [Risk] `0.0.0.0` 会让服务暴露给同一网络中的其他设备 → 仅通过显式 `SERVER_HOST` 开启，并提醒开发者使用可信局域网和系统防火墙。
- [Risk] HTTP 明文配置若误合入生产 variant 会降低传输安全 → 只放在 debug/profile manifest，并增加 release 配置检查。
- [Risk] Dart define 在构建后不会动态更新 → 更换 Mac IP 后必须重新执行 `flutter run` 或重新构建；这是编译期配置的预期限制。
