import os

from django import template
from django.conf import settings
from django.templatetags.static import static as static_url

register = template.Library()


@register.simple_tag
def static_v(path):
    """Like {% static %}, but appends the file's mtime as a cache-busting
    query param so browsers fetch a fresh copy whenever it changes on disk."""
    url = static_url(path)
    full_path = settings.BASE_DIR / "dashboard" / "static" / path
    try:
        version = int(os.path.getmtime(full_path))
    except OSError:
        version = 0
    return f"{url}?v={version}"
