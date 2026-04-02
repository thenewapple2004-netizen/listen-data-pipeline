from contextlib import asynccontextmanager
from fastapi import FastAPI

# Database engine and table creation
from db.db import create_db_and_tables

# Import models so SQLModel registers them before create_all() is called
import models.models  # noqa: F401

# Ingestion router
from routes.ingestion import router as ingestion_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing application...")
    create_db_and_tables()  # Connects to DB and creates all tables
    yield
    print("Application shutting down...")


app = FastAPI(
    lifespan=lifespan,
    title="Listen Data Pipeline",
    description="Batch ingestion API for Urdu words and sentences into the urdu_dict database.",
    version="1.0.0",
)

# ── Routers ──────────────────────────────────
app.include_router(ingestion_router)


# ── Health Check ─────────────────────────────
@app.get("/", tags=["Health"])
def root():
    """Health check — confirms server is up and database is connected."""
    return {"status": "ok", "message": "Listen Data Pipeline is running!"}