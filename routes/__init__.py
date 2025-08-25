"""
API Routes Package

This package contains all the API route definitions for the Travel Planner backend.
Routes are organized by feature/domain and imported here for easy access.
"""

# Import route modules here as they are created
from .travels import router as travels_router
# from .events import router as events_router
# from .users import router as users_router

# List of all routers for easy registration
__all__ = [
    "travels_router",
    # "events_router",
    # "users_router"
]
