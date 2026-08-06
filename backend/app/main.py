from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.scaffold import router as scaffold_router

from app.routes.analyze import router as analyze_router
from app.routes.molecule import router as molecule_router

app = FastAPI(
    title="Scaffold Analyzer API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(scaffold_router)
app.include_router(molecule_router)

@app.get("/")
def home():
    return {
        "message": "Scaffold Analyzer Backend Running"
    }