"""JARVIS 3.0 - Application Server & CLI Entrypoint."""
from contextlib import asynccontextmanager
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router as api_router
from core.config import get_settings
from core.health_manager import health_manager
from core.logger import get_logger
from engine.jarvis_engine import jarvis_engine

settings = get_settings()
logger = get_logger("Main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for JARVIS 3.0."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]...")
    report = health_manager.get_formatted_health_report()
    logger.info(f"\n{report}")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title="JARVIS 3.0 AI Operating System",
    description="Agentic Desktop AI Assistant with Deterministic Execution & Multi-Tier Verification",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Mount Frontend UI static files
frontend_dir = Path(__file__).parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/", tags=["Root"])
    async def serve_ui():
        return FileResponse(str(frontend_dir / "index.html"))
    
    @app.get("/style.css", tags=["Root"])
    async def serve_css():
        return FileResponse(str(frontend_dir / "style.css"))

    @app.get("/app.js", tags=["Root"])
    async def serve_js():
        return FileResponse(str(frontend_dir / "app.js"))
else:
    @app.get("/", tags=["Root"])
    async def root():
        return JSONResponse({
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "online",
            "health": "/api/health",
            "apps": "/api/apps",
            "tools": "/api/tools",
            "docs": "/docs",
        })


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "report": health_manager.get_formatted_health_report(),
        "subsystems": {k: v.model_dump() for k, v in health_manager.get_health().items()},
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
