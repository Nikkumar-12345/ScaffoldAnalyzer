# Deployment & local setup

## What changed (v1.2) - Homologous proteins

- **New panel "Homologous Proteins"** on the dashboard: the proteins whose
  sequence is most similar to the analysed target, with percent identity,
  coverage, bit score and E-value. Each homolog that has activity data links
  straight to its own analysis.
- **Selectivity read-out** on each scaffold's "Other Targets" list: targets that
  are sequence homologs of the analysed protein are marked with a badge and
  sorted to the top, so a scaffold shared across a protein family (a selectivity
  risk) is distinguishable from one shared with unrelated proteins.
- **How the comparison is done**: every target in the local ChEMBL database was
  aligned against every other target with a Smith-Waterman local alignment
  (BLOSUM62, gap open 11, extend 1) - the exact alignment that BLAST
  approximates heuristically. E-values use the standard Karlin-Altschul
  parameters for that scoring scheme. The results are precomputed into
  `backend/precomputed/homologs.db.gz`, so a search at runtime is a database
  lookup: no alignment, no network call, no new runtime dependency.
- **Adjustable cutoff, 70% by default**: a slider sets how similar a protein
  must be to count as homologous, and the whole dashboard (panel counts, ticks
  and the per-scaffold selectivity note) follows it. It can be switched between
  *similarity* (identical plus conservative substitutions - the usual reading of
  a "70% similarity" benchmark) and *identity* (identical residues only). Both
  numbers are always shown for every hit, and hits below the cutoff are one
  click away rather than discarded.

  The slider is bounded to the range where sequence comparison can actually say
  something, and each band is labelled:

  | Basis | Range | Twilight zone | Probable homolog | Same family | Close relative |
  |---|---|---|---|---|---|
  | Identity | 20-95% | 20-25% | 25-40% | 40-70% | 70%+ |
  | Similarity | 40-95% | 40-50% | 50-65% | 65-80% | 80%+ |

  Below the twilight zone, similarity cannot establish homology on its own,
  which is why the slider does not go lower.

  The starting position is set server-side:
  - `HOMOLOG_BENCHMARK` - the percentage, default `70`
  - `HOMOLOG_BENCHMARK_BASIS` - `similarity` (default) or `identity`
- **New endpoints**: `POST /homolog/search` and
  `POST /homolog/scaffold-selectivity`. `POST /scaffold/cross-targets` accepts an
  optional `query_uniprot_id` and then annotates each target with `identity`,
  `bit_score`, `evalue` and `is_homolog`; without it the response is byte for
  byte what it was before.
- The analysis result gains a `homologs` block and `summary.uniprot`. Everything
  else in the result is unchanged.

### Rebuilding the homolog cache

Only needed when the ChEMBL database changes. Requires network access to
UniProt and `pip install parasail` (build time only - the app itself does not
need it):

```bash
cd backend
python build_homolog_cache.py database/scaffold_analyzer_chembl.db \
    precomputed/homologs.db
# commit the generated precomputed/homologs.db.gz
```

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
