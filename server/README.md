# Red Book Editor Server

Python/FastAPI 模块化单体服务，负责账号、笔记、内容审核、模型适配、文件存储和发布记录。

## 本地运行

需要 Python 3.13、[uv](https://docs.astral.sh/uv/)、Docker 和 Docker Compose。
下面的命令都在 `server/` 目录执行。

### 第一次启动

```sh
cd server

# 1. 启动 PostgreSQL 容器
docker compose up -d postgres

# 2. 创建/同步 Python 虚拟环境和依赖
uv sync

# 3. 设置本地开发配置。真实生成使用 DeepSeek，需要 API Key。
export APP_ENV=development
export SERVER_PORT=8100
export DATABASE_URL=postgresql+asyncpg://red_book_editor:red_book_editor-local-only@127.0.0.1:5432/red_book_editor_development
export MODEL_PROVIDER=deepseek
export DEEPSEEK_API_KEY="你的 DeepSeek API Key"

# 4. 执行数据库迁移
make migrate

# 5. 启动 FastAPI 开发服务器
make run
```

`make run` 会启动 Uvicorn 的热重载模式，服务地址是
`http://127.0.0.1:8100`。8100 与 Godot AI MCP 默认使用的 8000 分离；修改 Python 文件后服务会自动重载。

### 后续启动

如果依赖、数据库和迁移都已经准备好，日常只需要：

```sh
cd server
docker compose up -d postgres
export APP_ENV=development
export SERVER_PORT=8100
export DATABASE_URL=postgresql+asyncpg://red_book_editor:red_book_editor-local-only@127.0.0.1:5432/red_book_editor_development
export MODEL_PROVIDER=deepseek
export DEEPSEEK_API_KEY="你的 DeepSeek API Key"
make run
```

环境变量只对当前终端窗口生效。也可以复制 `.env.example` 为本地 `.env`，服务会自动读取
`server/.env`；即使从仓库根目录启动，也会使用同一份配置（`.env` 不要提交到 Git），例如：

```sh
cp .env.example .env
make run
```

### 确认服务是否启动成功

另开一个终端执行：

```sh
curl --noproxy '*' http://127.0.0.1:8100/health/live
curl --noproxy '*' http://127.0.0.1:8100/health/ready
```

预期返回：

```json
{"status":"live"}
{"status":"ready","model_provider":"deepseek","model":"deepseek-chat","model_configured":"true"}
```

也可以打开 FastAPI 调试页面：<http://127.0.0.1:8100/docs>。
`ready` 表示应用生命周期已经初始化；它目前不主动执行数据库查询，所以数据库连接问题仍需结合 API 请求或日志判断。

### 查看状态、日志和停止服务

```sh
# 查看 PostgreSQL 容器状态
docker compose ps

# 查看 PostgreSQL 日志
docker compose logs -f postgres

# 停止 FastAPI：在运行 make run 的终端按 Ctrl-C

# 停止 PostgreSQL 容器，但保留本地数据卷
docker compose stop postgres

# 停止并移除容器，但保留本地数据卷
docker compose down
```

`docker compose down -v` 会额外删除 PostgreSQL 数据卷，除非确认要清空本地数据库，否则不要使用。

### 常见问题

- **访问 `8100` 失败**：确认 `make run` 的终端没有退出，并检查端口：`lsof -nP -iTCP:8100 -sTCP:LISTEN`。也可以用 `SERVER_PORT=8101 make run` 临时切换端口。
- **数据库连接失败**：先执行 `docker compose ps`，确认 `postgres` 状态为 `Up`，再执行 `make migrate`。
- **端口 `5432` 被占用**：停止其他 PostgreSQL，或修改 `docker-compose.yml` 的端口映射，并同步修改 `DATABASE_URL`。
- **生成接口没有调用模型**：访问 `/health/ready` 查看 `model_provider`。只有 `model_provider=deepseek` 才会请求 DeepSeek；`stub` 只用于测试和明确的离线开发，不代表真实生成质量。
- **遇到 SOCKS 代理相关错误**：检查当前终端的 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY`（也可能是小写形式）环境变量；本地健康检查可使用 `curl --noproxy '*' ...`，本地测试不需要代理时可以临时取消导出后再运行。

## 验证

```sh
make lock-check
make format-check
make typecheck
make test
make integration-test
```
