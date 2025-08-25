from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
import time
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

# Import our modules
from config.config import get_settings
from database.db import init_db, check_db_connection
from middleware.error_handler import add_error_handlers
from middleware.logger import setup_logging

# Import API routes
from routes import travels_router
from routes.events import router as events_router
from routes.eventTypes import router as event_types_router

# Configure logging
setup_logging()

logger = logging.getLogger(__name__)

# Global settings
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Travel Planner Backend Server...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Create uploads directory if it doesn't exist
    os.makedirs(settings.UPLOAD_PATH, exist_ok=True)
    
    logger.info(f"Server started successfully on port {settings.PORT}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Travel Planner Backend Server...")

# Create FastAPI app
app = FastAPI(
    title="Travel Planner API",
    description="Backend API for Travel Planner application",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Add custom error handlers
add_error_handlers(app)

# Include API routes
app.include_router(travels_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(event_types_router, prefix="/api")

# Mount static files for uploads
try:
    os.makedirs(settings.UPLOAD_PATH, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_PATH), name="uploads")
except Exception as e:
    logger.warning(f"Could not mount uploads directory: {e}")

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Health check endpoints
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "service": "travel-planner-backend"
    }

@app.get("/health/db")
async def database_health_check() -> Dict[str, Any]:
    """Database health check endpoint"""
    try:
        is_healthy = await check_db_connection()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "database": "connected" if is_healthy else "disconnected",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e),
            "timestamp": time.time()
        }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Travel Planner Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
