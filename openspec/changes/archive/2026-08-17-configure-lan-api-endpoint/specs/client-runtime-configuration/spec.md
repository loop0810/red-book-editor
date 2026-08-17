## Purpose

让 Flutter 客户端可以在构建或调试启动时选择可访问的服务端地址，从而支持真机通过局域网连接开发服务，同时保持本机开发的兼容默认值。

## ADDED Requirements

### Requirement: Configurable API base URL

客户端 SHALL 支持通过 `--dart-define=API_BASE_URL=<absolute URL>` 注入 API 基地址，并将该地址用于账号、栏目、笔记、素材和发布记录等所有服务端请求。

#### Scenario: Use the configured LAN endpoint

- **WHEN** 客户端以 `--dart-define=API_BASE_URL=http://192.168.1.23:8100` 构建或运行
- **THEN** 所有 API 请求 SHALL 发送到 `http://192.168.1.23:8100` 对应的服务端路径

#### Scenario: Preserve local development default

- **WHEN** 客户端没有提供 `API_BASE_URL`
- **THEN** API 基地址 SHALL 默认为 `http://127.0.0.1:8100`

#### Scenario: Normalize a trailing slash

- **WHEN** `API_BASE_URL` 以一个或多个 `/` 结尾
- **THEN** 客户端 SHALL 去除末尾斜杠后再拼接 API 路径，避免生成重复斜杠
