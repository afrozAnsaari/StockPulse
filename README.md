# StockPulse — AI-Driven Inventory Management & Dynamic Pricing

## Layout

- `backend/` — FastAPI, uv, local Python (`.python/`) and venv (`.venv/`)
- `frontend/` — React + Vite, npm dependencies (`node_modules/`)

## Backend

```powershell
cd backend
uv python install
uv sync
uv run python run.py
```

API: http://localhost:8000  |  Docs: http://localhost:8000/docs

Copy `backend/.env.example` to `backend/.env` and set `LLM_API_KEY`.

## Frontend

```powershell
cd frontend
npm install
npm run dev
```
