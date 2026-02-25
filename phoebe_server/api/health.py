"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "phoebe-server",
        "version": "0.1.0",
        "status": "running"
    }
