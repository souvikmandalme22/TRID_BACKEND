# TRID Backend

Production-grade FastAPI backend for TRID 3D printing platform.

## Setup

```bash
cp .env.example .env
docker-compose up -d
alembic upgrade head
uvicorn app.main:app --reload
```

## API Docs
http://localhost:8000/api/docs
