Local development
-----------------

1. Create a Python 3.11 virtualenv and activate it:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
```

2. Install dependencies (use pinned file for reproducible installs):

```powershell
pip install -r requirements-pinned.txt
```

3. Environment variables (minimum):

- `DATABASE_URL` (postgres SQLAlchemy URL)
- `REDIS_URL` (redis://host:port/db)
- `NEO4J_URI` (bolt://host:port)
- `APP_ENV` (development|staging|production)
- `LLM_PROVIDER` (e.g., `gemini` or `claude`)
- `LLM_API_URL` (self-hosted LLM endpoint, optional for Claude)
- `LLM_API_KEY` (your Claude/Gemini key)

Example `.env`:

```
DATABASE_URL=postgresql+psycopg://<DB_USER>:<DB_PASSWORD>@localhost:5432/govschemes
REDIS_URL=redis://localhost:6379/0
NEO4J_URI=bolt://localhost:7687
APP_ENV=development
LLM_PROVIDER=claude
LLM_API_URL=http://llm-host:8000/v1/generate
LLM_API_KEY=YOUR_CLAUDE_KEY
```

4. Run database migrations (configure `alembic/env.py` to import your metadata):

```powershell
alembic upgrade head
```

5. Run the app locally:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Docker / Container (any platform)
---------------------------------

Use `docker-compose.yml` in the repo root to run dependencies + backend. Set the LLM env vars in the `backend` service or provide a reachable LLM service.

```powershell
docker compose up --build
```

Notes about hosting & LLM keys
- For a self-hosted Claude-compatible server, set `LLM_PROVIDER=claude`, `LLM_API_URL` to the HTTP endpoint (e.g. `http://llm:8000/v1/generate`) and `LLM_API_KEY` to the key.
- The code prefers `LLM_API_KEY` and will fall back to `GEMINI_API_KEY` or `CLAUDE_API_KEY` if present to retain compatibility.

Troubleshooting
- If the LLM does not respond, the extractor will fall back to a regex-based extractor (lower quality).
- Run `pytest -q` to validate unit tests and `ruff check . --fix` to fix style issues.
