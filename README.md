# Gosling Drive

Backend file storage for uni project.

## Stack

### Backend
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- MinIO / S3-compatible object storage
- uv

### Frontend
- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui компоненты
- Sonner (toasts)

### Ops
- Docker Compose

## Local Run (Docker)

```bash
cp .env.example .env
docker-compose up --build
```

Endpoints:

- Web UI (Next.js): http://localhost:3000
- API: http://localhost:8000/api
- Swagger / OpenAPI: http://localhost:8000/docs
- Healthcheck: http://localhost:8000/health
- MinIO Console: http://localhost:9001

Default MinIO credentials: `minioadmin / minioadmin`.

## Local Run (без Docker)

Backend:

```bash
uv sync --all-groups
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Next.js dev на :3000 ребейзит `/api/*` → `http://localhost:8000/api/*` (см. `frontend/next.config.ts`), поэтому CORS не задействуется. Если бэкенд на другом хосте — выставь `BACKEND_INTERNAL_URL`.

## Multipart Upload Flow

Большие файлы уходят напрямую из браузера в MinIO:

```text
Browser -> MinIO
```

Бэкенд создаёт upload-сессию, проверяет права, выдаёт presigned URL на каждую часть, завершает multipart upload и пишет метаданные в PostgreSQL. Логика загрузки — `frontend/lib/upload.ts` (4 параллельных воркера на части).

## Версионирование

Новая версия существующего файла — тот же multipart-flow, просто другая точка инициализации:

```text
POST /api/files/{file_id}/versions/uploads
POST /api/uploads/{upload_session_id}/parts
POST /api/uploads/{upload_session_id}/complete
```

## Development

Тесты бэкенда:

```bash
uv run pytest
```

Smoke-проверка импортов и OpenAPI:

```bash
uv run python -c "from app.main import app; print(len(app.openapi()['paths']))"
```

Линт фронтенда:

```bash
cd frontend && npm run lint
```
