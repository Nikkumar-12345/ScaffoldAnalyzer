# Deployment & local setup

## What changed (v1.1)

- **Fast analysis**: a precomputed RDKit cache (`backend/precomputed/rdkit_cache.db.gz`)
  holds the Murcko scaffold, side chain and descriptors of every molecule and
  scaffold in the ChEMBL database. Results are identical to computing them live;
  anything not in the cache (e.g. ChEMBL API fallback targets) is computed live.
- Scaffold images are drawn only for the top 10 scaffolds (the ones shown).
  `all_scaffolds[*].svg` is `null` for the rest; fetch any image with
  `POST /scaffold/svg {"scaffold_smiles": "..."}`.
- **Progress bar**: `POST /analyze/start` -> `GET /analyze/status/{job_id}` ->
  `GET /analyze/result/{job_id}`. The original `POST /analyze/` still works.
- **Clear errors**: invalid UniProt format (400), ID not found (404), no usable
  activity data (422), ChEMBL unreachable (503).
- **Keep-alive**: the backend pings its own `/health` every 10 minutes on Render
  (uses `RENDER_EXTERNAL_URL`, set automatically). Backup: GitHub Actions
  workflow `.github/workflows/keep-backend-awake.yml`.
- Results are cached per UniProt ID, so repeat analyses are instant.

## Deploy

1. Commit and push to `main`. Render (backend, Docker, root directory `backend`)
   and Vercel (frontend, root directory `frontend`) redeploy automatically.
2. No new environment variables are required. Optional:
   - `KEEPALIVE_ENABLED=0` to turn the self-ping off
   - `KEEPALIVE_INTERVAL_SECONDS` (default 600)
   - `RESULT_CACHE_SIZE` (default 12 analyses kept in memory)
3. GitHub Actions: the keep-alive workflow runs automatically on the default
   branch. If the backend URL ever changes, set a repository variable
   `BACKEND_URL` (Settings -> Secrets and variables -> Actions -> Variables).

Note: on Render's free plan, one always-on service uses ~744 of the 750 free
instance hours per month. Render's paid Starter plan never sleeps and has 5x
the CPU, if you ever need it.

## Run locally (Windows, macOS, Linux)

Backend (Python 3.12, as in `runtime.txt`; Python 3.9 that ships with macOS is
too old for pandas 3 / numpy 2):

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The ChEMBL database downloads automatically on first start, and the
precomputed cache unpacks itself next to the `.gz` file.

Frontend:

```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev   # Windows PowerShell: $env:VITE_API_URL="http://localhost:8000"; npm run dev
```

## Rebuilding the precomputed cache

Only needed if the ChEMBL database or the RDKit version changes (the backend
ignores a cache built with a different RDKit version, so results stay exact):

```bash
cd backend
python build_precomputed_cache.py database/scaffold_analyzer_chembl.db precomputed/rdkit_cache.db
gzip -k precomputed/rdkit_cache.db   # commit precomputed/rdkit_cache.db.gz
```
