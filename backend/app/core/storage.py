from pathlib import Path
from urllib.parse import urlparse

from app.core.config import get_settings

MEDIA_URL_PREFIX = "/media"
STORAGE_ROOT = Path(__file__).resolve().parents[2] / "storage"
BRANDING_STORAGE_ROOT = STORAGE_ROOT / "company-branding"


def ensure_storage_root() -> None:
    BRANDING_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


def build_public_media_url(relative_path: str) -> str:
    settings = get_settings()
    base_url = settings.public_base_url.rstrip("/")
    path = relative_path.lstrip("/")
    return f"{base_url}{MEDIA_URL_PREFIX}/{path}"


def media_relative_path_from_url(url: str | None) -> Path | None:
    if not url:
        return None

    path = urlparse(url).path
    if not path.startswith(f"{MEDIA_URL_PREFIX}/"):
        return None

    return Path(path.removeprefix(f"{MEDIA_URL_PREFIX}/"))
