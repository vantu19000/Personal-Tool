"""Application settings (per-tool configuration blocks).

Import :data:`router` from here and include it in the FastAPI app. The blocks
themselves live in :mod:`app.core.settings_store`.
"""
from app.settings.router import router

__all__ = ["router"]
