from datetime import UTC, datetime, timedelta

import structlog
from bson import ObjectId
from fastapi import APIRouter, Cookie, HTTPException, Response, status

from app.api.deps import CurrentUser
from app.api.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_password,
    verify_token,
)
from app.db.repositories import token_blocklist_repository, user_repository

logger = structlog.get_logger()

router = APIRouter()

REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
ACCESS_TOKEN_COOKIE_NAME = "access_token"


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        secure=settings.environment == "production",
        samesite="lax",
        path="/api/v1/auth",
    )


def set_access_cookie(response: Response, access_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/api/v1",
    )


def clear_access_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        secure=settings.environment == "production",
        samesite="lax",
        path="/api/v1",
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(response: Response, request: RegisterRequest):
    existing = await user_repository.get_by_email(request.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = await user_repository.create(request)
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    await user_repository.add_refresh_token(user.id, refresh_token)
    set_access_cookie(response, access_token)
    set_refresh_cookie(response, refresh_token)
    logger.info("User registered", user_id=str(user.id))
    return TokenResponse(
        access_token=access_token,
        expires_in=get_settings().access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(response: Response, request: LoginRequest):
    user = await user_repository.get_by_email(request.email)
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive")

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    await user_repository.add_refresh_token(user.id, refresh_token)
    await user_repository.update_last_login(user.id)

    set_access_cookie(response, access_token)
    set_refresh_cookie(response, refresh_token)

    logger.info("User logged in", user_id=str(user.id))
    return TokenResponse(
        access_token=access_token,
        expires_in=get_settings().access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    request: RefreshRequest | None = None,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_TOKEN_COOKIE_NAME),
):
    refresh_token = request.refresh_token if request and request.refresh_token else refresh_cookie
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
    user_id_str = verify_token(refresh_token, "refresh")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = ObjectId(user_id_str)
    if not await user_repository.verify_refresh_token(user_id, refresh_token):
        await user_repository.clear_refresh_tokens(user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    if await token_blocklist_repository.exists(hash_refresh_token(refresh_token)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    user = await user_repository.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not found or inactive")

    await token_blocklist_repository.add(
        hash_refresh_token(refresh_token), user_id, datetime.now(UTC) + timedelta(days=7)
    )
    await user_repository.remove_refresh_token(user_id, refresh_token)

    new_access_token = create_access_token(str(user_id))
    new_refresh_token = create_refresh_token(str(user_id))

    await user_repository.add_refresh_token(user_id, new_refresh_token)
    set_access_cookie(response, new_access_token)
    set_refresh_cookie(response, new_refresh_token)

    logger.info("Token refreshed", user_id=str(user_id))
    return TokenResponse(
        access_token=new_access_token,
        expires_in=get_settings().access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(
    response: Response,
    current_user: CurrentUser,
    request: RefreshRequest | None = None,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_TOKEN_COOKIE_NAME),
):
    refresh_token = request.refresh_token if request and request.refresh_token else refresh_cookie
    if refresh_token:
        token_hash = hash_refresh_token(refresh_token)
        await token_blocklist_repository.add(token_hash, current_user.id, datetime.now(UTC) + timedelta(days=7))
        await user_repository.remove_refresh_token(current_user.id, refresh_token)

    clear_refresh_cookie(response)
    clear_access_cookie(response)
    logger.info("User logged out", user_id=str(current_user.id))
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


@router.patch("/me", response_model=UserResponse)
async def update_me(current_user: CurrentUser, request: UserUpdateRequest):
    updated = await user_repository.update(current_user.id, request)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(
        id=str(updated.id),
        email=updated.email,
        full_name=updated.full_name,
        is_active=updated.is_active,
        is_superuser=updated.is_superuser,
        created_at=updated.created_at,
        last_login=updated.last_login,
    )
