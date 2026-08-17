## Purpose

定义 Mac 上的开发服务如何监听局域网，以及 Android 调试构建如何安全地访问本地 HTTP 服务，确保真机调试不依赖 USB 端口转发。

## ADDED Requirements

### Requirement: Bind the development server to a selectable host

开发服务 SHALL 支持通过 `SERVER_HOST` 选择监听地址，默认值 SHALL 保持为 `127.0.0.1`；当设置为 `0.0.0.0` 时，服务 SHALL 接受来自 Mac 局域网网卡的连接。

#### Scenario: Keep loopback-only default

- **WHEN** 开发者未设置 `SERVER_HOST`
- **THEN** 服务 SHALL 仅监听 `127.0.0.1`，保持现有本机开发隔离行为

#### Scenario: Expose the service for LAN debugging

- **WHEN** 开发者使用 `SERVER_HOST=0.0.0.0` 启动服务，并且手机与 Mac 位于可互通的局域网
- **THEN** 手机通过 Mac 局域网 IP 和服务端口访问 `/health/live` SHALL 获得成功响应

### Requirement: Permit cleartext traffic only for development Android variants

Android debug 和 profile 构建 SHALL 允许访问开发环境的 HTTP API；release 构建 SHALL 不因本变更默认开启全局明文 HTTP。

#### Scenario: Debug device accesses HTTP API

- **WHEN** Android debug 或 profile 构建使用 HTTP 类型的 `API_BASE_URL`
- **THEN** 客户端 SHALL 允许该请求进入网络栈，而不因 Android 明文流量策略在客户端侧被拦截

#### Scenario: Release keeps production transport boundary

- **WHEN** Android release 构建运行
- **THEN** 本变更 SHALL 不增加 release manifest 的明文 HTTP 放行配置
