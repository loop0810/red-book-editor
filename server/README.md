# Red Book Editor Server

Python/FastAPI 模块化单体服务，负责账号、笔记、内容审核、模型适配、文件存储和发布记录。

## 本地运行

需要 Python 3.13、uv、Docker 和 Docker Compose：

```sh
docker compose up -d postgres
uv sync
export APP_ENV=development
export DATABASE_URL=postgresql+asyncpg://red_book_editor:red_book_editor-local-only@127.0.0.1:5432/red_book_editor_development
make migrate
make run
```

存活检查为 `GET /health/live`，就绪检查为 `GET /health/ready`。

## 验证

```sh
make lock-check
make format-check
make typecheck
make test
make integration-test
```
