from cryptography.fernet import Fernet

from app.config import get_settings

_settings = get_settings()


def _get_fernet() -> Fernet:
    key = _settings.secrets_encryption_key
    if not key:
        raise RuntimeError("SECRETS_ENCRYPTION_KEY not set in environment")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        return ""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()


def generate_encryption_key() -> str:
    return Fernet.generate_key().decode()
