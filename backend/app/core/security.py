import hashlib
from datetime import UTC, datetime, timedelta

import bcrypt
import structlog
from jose import JWTError, jwt

from app.config import get_settings

logger = structlog.get_logger()

def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    to_encode = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_token(token: str, token_type: str = "access") -> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != token_type:
            return None
        return payload.get("sub")
    except JWTError as e:
        logger.debug("Token verification failed", error=str(e), token_type=token_type)
        return None


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def hash_refresh_token(token: str) -> str:
    return f"sha256:{hashlib.sha256(token.encode()).hexdigest()}"


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token, returning the payload."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e


def encrypt_value(value: str) -> str:
    """Encrypt a secret or fail without ever returning plaintext as ciphertext."""
    from app.safety.secrets import encrypt_secret

    return encrypt_secret(value)


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a secret or fail closed when the value/key is invalid."""
    from app.safety.secrets import decrypt_secret

    return decrypt_secret(ciphertext)
