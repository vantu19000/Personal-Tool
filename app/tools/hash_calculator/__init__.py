"""Hash Calculator tool package.

Re-exports the tool's :class:`~fastapi.APIRouter` so callers can do
``from app.tools.hash_calculator import router`` and receive the router
*instance* (not the ``router`` submodule).
"""
from .router import router

__all__ = ["router"]