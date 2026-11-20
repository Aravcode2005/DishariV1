# DishariV1
Official Repository for Dishari@Google

## Local FastAPI backend (Windows PowerShell)

Requires Python 3.10 or newer. From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

If PowerShell blocks activation, use the environment interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

API: http://127.0.0.1:8000
Swagger: http://127.0.0.1:8000/docs
Health: http://127.0.0.1:8000/health
Stop the foreground server with Ctrl+C.

CORS permits localhost and 127.0.0.1 on ports 3000 and 5173 by default.
To change the explicit origins, set an environment variable before starting:

```powershell
$env:CORS_ORIGINS = "http://localhost:3000,http://localhost:5173"
```

See backend/.env.example for the configuration format. No credentials are
required. Files named .env are ignored and are not automatically loaded.

With the server running, open another terminal in backend and run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

See [backend/README.md](backend/README.md) for the modular MVP APIs, JSON example rules, optional PostgreSQL, synthetic uploads, tests, and Docker instructions.
