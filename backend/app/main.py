import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from rdkit import RDLogger

from app.routes.scaffold import router as scaffold_router

from app.routes.analyze import router as analyze_router
from app.routes.molecule import router as molecule_router

from app.services.database_service import DatabaseService
from app.services.keepalive_service import start_keepalive
from app.services.precomputed_service import PrecomputedService


# RDKit prints thousands of harmless warnings ("bond found with stereo
# spec but no stereo atoms") which slow down logging. Errors still show.
RDLogger.DisableLog("rdApp.warning")


def warm_up():
    """Open the database and precomputed cache before the first request."""

    try:
        DatabaseService.ensure_database_exists()
        PrecomputedService.is_available()
    except Exception as error:
        print(f"Warm-up warning: {error}")


@asynccontextmanager
async def lifespan(app):

    # Run in the background so the server binds its port immediately
    threading.Thread(target=warm_up, daemon=True).start()

    start_keepalive()

    yield


app = FastAPI(
    title="Scaffold Analyzer API",
    version="1.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compress large JSON responses (molecule details, cross-targets)
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,
    compresslevel=6
)

app.include_router(analyze_router)
app.include_router(scaffold_router)
app.include_router(molecule_router)

@app.get("/")
def home():
    return {
        "message": "Scaffold Analyzer Backend Running"
    }


# Lightweight endpoint for keep-alive pings and uptime monitors
@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {
        "status": "ok"
    }
