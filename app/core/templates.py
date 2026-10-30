"""A single shared Jinja2 environment for the whole app.

Every route (dashboard + tools) should import ``templates`` from here instead of
creating its own instance, so that the globals below are available in all
templates without having to pass them on every request.
"""
from fastapi.templating import Jinja2Templates
from jinja2 import pass_context

from app.core.config import settings, TOOLS
from app.core.i18n import (
    get_current_locale,
    get_supported_locales,
    t as i18n_t,
)

templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


class CurrentLangProxy:
    """Smart proxy allowing `current_lang` to work as a variable, function, or string."""

    def __str__(self) -> str:
        return get_current_locale()

    def __repr__(self) -> str:
        return get_current_locale()

    def __call__(self, *args, **kwargs) -> str:
        return get_current_locale()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CurrentLangProxy):
            return get_current_locale() == str(other)
        return get_current_locale() == other

    def __hash__(self) -> int:
        return hash(get_current_locale())


current_lang_proxy = CurrentLangProxy()


@pass_context
def jinja_t(context, key: str, default: str | None = None, **kwargs) -> str:
    """Template translation function supporting auto-detected request locale."""
    request = context.get("request")
    req_lang = getattr(request.state, "lang", None) if request and hasattr(request, "state") else None
    locale = kwargs.pop("lang", None) or kwargs.pop("locale", None) or req_lang or get_current_locale()
    return i18n_t(key, locale=locale, default=default, **kwargs)


# Globals available in every template.
templates.env.globals["settings"] = settings
templates.env.globals["tools"] = TOOLS
templates.env.globals["t"] = jinja_t
templates.env.globals["current_lang"] = current_lang_proxy
templates.env.globals["get_supported_locales"] = get_supported_locales

# Also support pipe filter syntax: {{ 'common.save' | t }}
templates.env.filters["t"] = jinja_t
