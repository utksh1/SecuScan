"""
SecuScan Backend - Main application entry point
"""

import logging
import sys
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from .request_middleware import RequestIDMiddleware

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .auth import init_api_key
from .cache import init_cache, cache as global_cache
from .database import init_db, db as global_db
from .plugins import init_plugins
from .routes import router
from .executor import recover_tasks_on_startup
import backend.secuscan.executor as _executor_module
from .saved_views import saved_views_router
from .workflows import scheduler

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.log_file)
        if Path(settings.log_file).parent.exists()
        else logging.NullHandler()
    ]
)

from .logging_utils import RequestIDFilter, JSONFormatter

for handler in logging.getLogger().handlers:
    handler.addFilter(RequestIDFilter())
    handler.setFormatter(JSONFormatter())

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting SecuScan backend...")
    
    # Ensure directories exist
    settings.ensure_directories()
    logger.info("✓ Directories initialized")

    # Initialize API key authentication
    api_key = init_api_key(settings.data_dir)
    logger.info("✓ API key authentication ready (key file: %s/.api_key)", settings.data_dir)
    
    # Initialize database
    await init_db(settings.database_path)
    logger.info("✓ SQLite connected")

    await init_cache()
    logger.info("✓ In-memory cache initialized")
    
    # Load plugins
    await init_plugins(settings.plugins_dir)
    logger.info("✓ Plugins loaded")

    # If docker is enabled, verify and auto-create the restricted docker network
    if settings.docker_enabled:
        if shutil.which("docker"):
            logger.info(f"Docker is enabled. Verifying network '{settings.docker_network}'...")
            try:
                import subprocess
                res = subprocess.run(
                    ["docker", "network", "inspect", settings.docker_network],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if res.returncode != 0:
                    logger.info(f"Docker network '{settings.docker_network}' not found. Creating isolated bridge network (ICC disabled)...")
                    creation_res = subprocess.run(
                        [
                            "docker", "network", "create",
                            "--driver", "bridge",
                            "--opt", "com.docker.network.bridge.enable_icc=false",
                            settings.docker_network
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if creation_res.returncode != 0:
                        logger.warning("Failed to create isolated bridge network with ICC disabled. Falling back to standard bridge...")
                        subprocess.run(
                            ["docker", "network", "create", "--driver", "bridge", settings.docker_network],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        logger.info(f"✓ Docker network '{settings.docker_network}' created (fallback)")
                    else:
                        logger.info(f"✓ Docker network '{settings.docker_network}' created with ICC disabled")
                else:
                    logger.info(f"✓ Docker network '{settings.docker_network}' verified")
            except Exception as e:
                logger.warning(f"Failed to check/create Docker network '{settings.docker_network}': {e}")
        else:
            logger.warning("Docker sandboxing is enabled but 'docker' executable is not in PATH.")

    # Recover tasks that were mid-flight or queued when the backend last stopped.
    # This runs synchronously (before yield) so the HTTP server only starts
    # accepting traffic after every interrupted task has been accounted for.
    _recovery_result = await recover_tasks_on_startup(global_db)
    _executor_module._last_recovery_result = _recovery_result
    logger.info(
        "✓ Startup recovery: %d running->failed, %d queued re-enqueued",
        _recovery_result["recovered_running"],
        _recovery_result["recovered_queued"],
    )

    await scheduler.start()
    logger.info("✓ Workflow scheduler started")
    
    logger.info("✓ Ready to serve on %s:%d", settings.bind_address, settings.bind_port)
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down SecuScan backend...")
    if global_db:
        await global_db.disconnect()
    if global_cache:
        await global_cache.disconnect()
    await scheduler.stop()
    logger.info("✓ Shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="SecuScan API",
    description="Backend for SecuScan Pentesting Toolkit",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

@app.get("/api/docs", include_in_schema=False)
async def redirect_api_docs():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

@app.get("/api/redoc", include_in_schema=False)
async def redirect_api_redoc():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/redoc")

@app.get("/api/openapi.json", include_in_schema=False)
async def redirect_api_openapi():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/openapi.json")

# CORS middleware
cors_allow_all = "*" in settings.cors_allowed_origins
if cors_allow_all and settings.cors_allow_credentials:
    logger.warning(
        "CORS configured with '*' origin and credentials enabled. "
        "Disabling credentials to keep browser behavior valid."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=settings.cors_allow_credentials and not cors_allow_all,
    allow_methods=settings.cors_allowed_methods,
    allow_headers=settings.cors_allowed_headers,
)
app.add_middleware(RequestIDMiddleware)

# Include API routes
app.include_router(router)
app.include_router(saved_views_router)


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
            "docker_available": shutil.which("docker") is not None,
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
        "backend.secuscan.main:app",
        host=settings.bind_address,
        port=settings.bind_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

if __name__ == "__main__":
    main()
