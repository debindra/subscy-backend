# Subscription Tracking API (FastAPI)

Parallel Python backend for incremental migration from NestJS.

## Quickstart

1. Create venv and install deps:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run dev server:

```
uvicorn app.main:app --reload --port 3001
```

3. Configure env (optional):
- `FRONTEND_URL`: comma-separated origins for CORS
- `NODE_ENV`: `development` or `production`

Open docs: http://localhost:3001/docs

## Structure
- `app/main.py`: FastAPI app, CORS, routers
- `app/core/security.py`: JWT + password hashing
- `app/routers/*.py`: Route groups (`auth`, `subscriptions`, `analytics`, `devices`)
- `app/schemas/*.py`: Pydantic models

This service mirrors the existing NestJS API contracts for a smooth cutover.

