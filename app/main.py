"""FitAI API app entrypoint.

This module creates the FastAPI application, registers routers, and configures middleware.
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from . import database
from .routers import auth, telemetry, recovery

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    database.Base.metadata.create_all(bind=database.engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="FitAI API",
        version="0.5.0 (Secured SaaS)",
        description="Intelligent physical activity monitoring and recovery forecasting",
        lifespan=lifespan,
    )

    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(auth.router, tags=["auth"])
    app.include_router(telemetry.router, tags=["telemetry"])
    app.include_router(recovery.router, tags=["recovery"])

    return app


app = create_app()


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "0.5.0"}


FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/{filename:path}")
async def serve_static(filename: str):
    """Serve frontend static files (JS, CSS, icons, manifest, sw.js)."""
    file_path = os.path.join(FRONTEND_DIR, filename)
    if os.path.isfile(file_path) and not filename.startswith("."):
        return FileResponse(file_path)
                                                             
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)