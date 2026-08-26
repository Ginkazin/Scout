from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import (
    AccessTokenResponse,
    LoginRequest,
    TokenResponse,
)
from app.schemas.user_schema import UserCreate, UserResponse
from app.services.auth_service import AuthService
from app.api.dependencies import get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

# Endpoint para registro de usuário
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        return await auth_service.register(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))from e 

# Endpoint para login do usuário
@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        tokens = await auth_service.login(str(data.email), data.password)

        response.set_cookie(
            key="refresh_token",
            value= tokens["refresh_token"],
            httponly=True,
            secure=False, #trocar para true quando tiver em produção
            samesite="lax",
            path="/auth",
            max_age=60 * 60 * 24 * 7
        )

        return TokenResponse(
            access_token=tokens["access_token"],
        )

    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc),) from exc
    
# Endpoint para refresh do token de acesso
@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    refresh_token: str | None = Cookie(default=None),
    auth_service: AuthService = Depends(get_auth_service),
):
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token ausente",
        )
    try:
        return await auth_service.refresh(refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

# Endpoint de logout
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/auth",
    )