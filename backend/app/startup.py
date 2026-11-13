"""Cloud entrypoint: validate, migrate a direct connection, then serve one origin."""
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

from alembic import command
from alembic.config import Config


def configure_runtime():
    from app.config import get_settings
    origin = os.environ.get("STUDYMATE_PUBLIC_ORIGIN") or os.environ.get("RENDER_EXTERNAL_URL", "")
    if origin:
        origin = origin.strip().rstrip("/")
        value = urlsplit(origin)
        _ = value.port
        if value.scheme != "https" or not value.hostname or value.username or value.password or value.path or value.query or value.fragment:
            raise ValueError("Public origin must be one HTTPS origin without credentials, path or query")
        os.environ["STUDYMATE_PUBLIC_ORIGIN"] = origin
    get_settings.cache_clear()
    settings = get_settings()
    settings.validate_for_startup()
    if settings.app_env == "production":
        if not settings.public_origin:
            raise ValueError("Set STUDYMATE_PUBLIC_ORIGIN or use RENDER_EXTERNAL_URL")
        if not (Path(settings.frontend_dist_dir) / "index.html").is_file():
            raise ValueError("Production frontend build is missing")
    port = int(os.environ.get("PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    return settings, port


def main():
    _, port = configure_runtime()
    command.upgrade(Config("alembic.ini"), "head")
    # HTTPS origin is explicit; untrusted X-Forwarded-* never defines identity/origin.
    os.execvp(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app", "--host", os.environ.get("BIND_HOST", "0.0.0.0"), "--port", str(port), "--no-proxy-headers"])


if __name__ == "__main__":
    main()
