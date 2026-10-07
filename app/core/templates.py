"""A single shared Jinja2 environment for the whole app.

Every route (dashboard + tools) should import ``templates`` from here instead of
creating its own instance, so that the globals below are available in all
templates without having to pass them on every request.
"""
from fastapi.templating import Jinja2Templates

from app.core.config import settings, TOOLS

templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

# Globals available in every template.
templates.env.globals["settings"] = settings
templates.env.globals["tools"] = TOOLS
