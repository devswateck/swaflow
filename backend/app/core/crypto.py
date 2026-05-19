import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _fernet() -> Fernet:
    settings = get_settings()
    raw_key = settings.encryption_key or settings.jwt_secret_key
    try:
        key_bytes = raw_key.encode()
        base64.urlsafe_b64decode(key_bytes)
        if len(key_bytes) == 44:
            return Fernet(key_bytes)
    except Exception:
        pass
    digest = hashlib.sha256(raw_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()

