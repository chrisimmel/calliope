"""
Version 2 of the Calliope API, featuring asynchronous processing.
"""

from fastapi import APIRouter

from .stories import router as stories_router
from .tasks import router as tasks_router

# Create a router that includes all v2 endpoints
router = APIRouter(prefix="/v2")

# Include the stories and tasks routers
router.include_router(stories_router)
router.include_router(tasks_router)

__all__ = ["router"]
