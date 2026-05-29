"""
main.py
FastAPI application entry point.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.api.routes import router
from backend.api.auth import router as auth_router
from backend.api.movement import router as movement_router
from backend.api.pose_ws import router as pose_ws_router
from backend.api.profile import router as profile_router
from backend.api.dashboard import router as dashboard_router
from backend.api.workout import router as workout_router
from backend.db.session import init_db
from backend.config import get_settings

settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    print("=" * 50)
    print("  CyberTrainer AI service starting")
    print("=" * 50)
    init_db()

    # Indexing ChromaDB can take a long time on Windows and should not block
    # health checks or the Web UI. Enable it only when rebuilding the local KB.
    if os.getenv("CYBERTRAINER_INDEX_ON_STARTUP") == "1":
        try:
            from backend.rag import index_knowledge_seed
            count = index_knowledge_seed()
            print(f"  Knowledge base indexed: {count} chunks")
        except ImportError:
            print("  Knowledge base: ChromaDB not installed, skipping")
        except Exception as e:
            print(f"  Knowledge base indexing skipped: {e}")
    else:
        print("  Knowledge base indexing skipped at startup")

    yield
    print("\n[info] service closed")


# create FastAPI application
app = FastAPI(
    title="CyberTrainer AI API",
    description="LLM-powered fitness movement analysis and training guidance system",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS config - restrict to configured frontend URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# register routers
app.include_router(router)
app.include_router(auth_router)
app.include_router(movement_router)
app.include_router(profile_router)
app.include_router(pose_ws_router)
app.include_router(dashboard_router)
app.include_router(workout_router)


FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    async def serve_frontend_index():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend_app(full_path: str):
        target = FRONTEND_DIST / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
