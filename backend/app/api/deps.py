import hashlib
from typing import Annotated

import structlog
from bson import ObjectId
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import verify_token
from app.db.models import UserInDB
from app.db.repositories import token_blocklist_repository, user_repository

logger = structlog.get_logger()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def _hash_token(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


async def get_current_user_id(
    request: Request,
    bearer_token: str = Depends(oauth2_scheme),
    cookie_token: str | None = Cookie(default=None, alias="access_token"),
) -> ObjectId:
    token = bearer_token or cookie_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if await token_blocklist_repository.exists(f"sha256:{_hash_token(token)}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = verify_token(token, "access")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return ObjectId(user_id_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(user_id: ObjectId = Depends(get_current_user_id)) -> UserInDB:
    user = await user_repository.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive")
    return user


async def get_optional_user(token: str | None = Header(None, alias="Authorization")) -> ObjectId | None:
    if not token or not token.startswith("Bearer "):
        return None
    raw_token = token[7:]
    if await token_blocklist_repository.exists(f"sha256:{_hash_token(raw_token)}"):
        return None
    user_id_str = verify_token(raw_token, "access")
    if not user_id_str:
        return None
    try:
        return ObjectId(user_id_str)
    except Exception:
        return None


CurrentUserId = Annotated[ObjectId, Depends(get_current_user_id)]
CurrentUser = Annotated[UserInDB, Depends(get_current_user)]
OptionalUserId = Annotated[ObjectId | None, Depends(get_optional_user)]
