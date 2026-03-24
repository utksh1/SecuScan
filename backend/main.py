"""
SecuScan Backend - Main application entry point
"""

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from cache import init_cache, cache as global_cache
from database import init_db, db as global_db
from plugins import init_plugins
from routes import router


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.log_file) if Path(settings.log_file).parent.exists() else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting SecuScan backend...")
    
    # Ensure directories exist
    settings.ensure_directories()
    logger.info("✓ Directories initialized")
    
    # Initialize database
    await init_db(settings.database_path)
    logger.info("✓ SQLite connected")

    await init_cache()
    logger.info("✓ In-memory cache initialized")
    
    # Load plugins
    await init_plugins(settings.plugins_dir)
    logger.info("✓ Plugins loaded")
    
    logger.info("✓ Ready to serve on %s:%d", settings.bind_address, settings.bind_port)
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down SecuScan backend...")
    if global_db:
        await global_db.disconnect()
    if global_cache:
        await global_cache.disconnect()
    logger.info("✓ Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="SecuScan API",
    description="Local-first pentesting toolkit backend",
    version="0.1.0-alpha",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)


# CORS middleware (restrict to localhost in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


# Health check endpoint
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    import platform
    import sys
    
    return {
        "status": "operational",
        "version": "0.1.0-alpha",
        "system": {
            "platform": platform.system(),
            "python_version": sys.version.split()[0],
            "docker_available": True,  # TODO: Check Docker availability
        }
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "SecuScan API",
        "version": "0.1.0-alpha",
        "status": "under development",
        "api_docs": f"{settings.base_url}/api/docs" if settings.debug else None,
        "legal_notice": "For authorized testing only. Unauthorized scanning may be illegal."
    }


def main():
    """Main entry point"""
    import uvicorn
    
    logger.info("""
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║              SecuScan v0.1.0-alpha                    ║
    ║         Local-First Pentesting Toolkit               ║
    ║                                                       ║
    ║  ⚠️  For authorized testing only                      ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "backend.main:app",
        host=settings.bind_address,
        port=settings.bind_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
