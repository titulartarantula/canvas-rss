"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from src.api.routes import dashboard, features, options

app = FastAPI(
    title="Canvas Feature Tracker API",
    description="API for tracking Canvas LMS feature options and deployment readiness",
    version="1.0.0",
)

# Register routers
app.include_router(dashboard.router)
app.include_router(features.router)
app.include_router(options.router)

# Static files will be mounted after frontend build exists
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


# Serve frontend for all non-API routes (after routes are registered)
# This will be configured after frontend is built
