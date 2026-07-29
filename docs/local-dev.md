# Local development (Windows)

## Important: `.env` is not “activated”

Unlike a Python virtualenv, you do **not** run `activate` for Next.js env files.

| File | What it does |
|---|---|
| `apps/web/.env.local` | Loaded **automatically** when you `npm run dev` or `npm run build` |
| `apps/web/.env.example` | Template only — copy to `.env.local` if missing |
| Root `.env.example` | Notes for optional API vars |

Next only exposes variables that start with `NEXT_PUBLIC_` to the browser.

Minimum web env:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

If you change `.env.local`, **restart** `npm run dev` (env is read at startup).

## You need two processes

LAoN is **API + web**. `npm run dev` alone is not enough.

### Terminal 1 — API (port 8000)

```powershell
cd C:\Users\aerok\LAoN\services\api
.\.venv\Scripts\activate
# first time only:
# pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Check: http://localhost:8000/health  
Docs: http://localhost:8000/docs  

No API `.env` is required for basic catalog/match/research.

### Terminal 2 — Web (port 3000)

```powershell
cd C:\Users\aerok\LAoN\apps\web
# first time only:
# copy .env.example .env.local
# npm install
npm run dev
```

Check: http://localhost:3000  
Research capture: http://localhost:3000/research  
Visitor camera: http://localhost:3000/visit  

## First-time setup (if you just cloned)

```powershell
cd C:\Users\aerok\LAoN

# API
cd services\api
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Web
cd ..\..\apps\web
copy .env.example .env.local
npm install
```

## Common issues

| Symptom | Fix |
|---|---|
| Catalog empty / “Could not reach the API” | Start Terminal 1 (uvicorn on 8000) |
| Research page fails to load | Same — API must be up |
| Camera / match works but no env “active” | Normal — check `.env.local` exists; restart `npm run dev` |
| Changed `.env.local` but no effect | Stop Next (Ctrl+C), run `npm run dev` again |
| Port in use | Close other Node/Python on 3000/8000, or use `--port 3001` |
| Phone can’t open camera app | Use PC LAN IP + same Wi‑Fi: `http://192.168.x.x:3000/visit` and set `NEXT_PUBLIC_API_URL=http://192.168.x.x:8000` then restart Next |

## Optional API env vars

```powershell
$env:PRIVATE_CORPUS_PATH = "C:\Users\aerok\LAoN\data\private"
$env:LAON_LOCAL_DIR = "C:\Users\aerok\LAoN\data\local"
$env:LAON_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
```

These are only needed for custom paths / CORS; defaults work on this machine.
