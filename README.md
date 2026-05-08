# Gosling Drive

Backend file storage for uni project.

## Stack

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- MinIO / S3-compatible object storage
- Docker Compose
- uv

## Local Run

Create local environment file:

```bash
cp .env.example .env
```

Install local dependencies:

```bash
uv sync --all-groups
```

Start services:

```bash
docker-compose up --build
```

Application endpoints:

- Web UI: http://localhost:8000
- Swagger/OpenAPI: http://localhost:8000/docs
- Healthcheck: http://localhost:8000/health
- MinIO Console: http://localhost:9001

Default local MinIO credentials:

```text
minioadmin / minioadmin
```

## Multipart Upload Flow

Large files are uploaded directly from browser to MinIO:

```text
Browser -> MinIO
```

The backend creates upload sessions, checks access rules, issues presigned URLs for
parts, completes multipart upload, and stores file metadata in PostgreSQL.

## Development

Run tests:

```bash
uv run pytest
```

Run an import/OpenAPI smoke check:

```bash
uv run python -c "from app.main import app; print(len(app.openapi()['paths']))"
```
