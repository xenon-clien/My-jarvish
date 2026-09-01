"""JARVIS AI Assistant - Main Application Entrypoint."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.health import router as health_router
from backend.api.routes import router as api_router
from backend.core.config import get_settings
from backend.core.logger import get_logger
from backend.database.database import db_manager

settings = get_settings()
logger = get_logger("Main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for application startup and shutdown."""
    logger.info(f"🚀 Starting {settings.APP_NAME} in {settings.APP_ENV} mode...")
    # Initialize SQLite database schema
    try:
        db_manager.initialize_schema()
    except Exception as exc:
        logger.error(f"Failed to initialize database schema: {exc}")
    yield
    logger.info(f"🛑 Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title="JARVIS Personal AI Assistant",
    description="Backend API and Agent Engine for JARVIS on Windows",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for local web dashboards and frontend tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Register Routers
app.include_router(health_router)
app.include_router(api_router)

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/", tags=["Root"])
async def root():
    """Serve glowing 3D Arc Reactor UI."""
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({
        "name": settings.APP_NAME,
        "status": "online",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
