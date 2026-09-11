from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.exceptions import ConflictError, NotFoundError, PlanLimitExceededError
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.server_repository import ServerRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.server_schema import ServerCreate, ServerResponse, ServerUpdate
from app.services.server_service import ServerService

router = APIRouter(tags=["servers"])

def get_server_service(db: AsyncSession = Depends(get_db)) -> ServerService:
    return ServerService(
        server_repository=ServerRepository(db),
        customer_repository=CustomerRepository(db),
        subscription_repository=SubscriptionRepository(db),
        plan_repository=PlanRepository(db),
    )


@router.post(
    "/customers/{customer_id}/servers",
    response_model=ServerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_server(
    customer_id: UUID,
    data: ServerCreate,
    current_user: User = Depends(get_current_user),
    service: ServerService = Depends(get_server_service),
):
    try:
        return await service.create(customer_id=customer_id, data=data, current_user=current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PlanLimitExceededError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/customers/{customer_id}/servers", response_model=list[ServerResponse])
async def list_servers_by_customer(
    customer_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: ServerService = Depends(get_server_service),
):
    try:
        return await service.list_by_customer(
            customer_id=customer_id, current_user=current_user, skip=skip, limit=limit
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ServerService = Depends(get_server_service),
):
    try:
        return await service.get_by_id(server_id=server_id, current_user=current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: UUID,
    data: ServerUpdate,
    current_user: User = Depends(get_current_user),
    service: ServerService = Depends(get_server_service),
):
    try:
        return await service.update(server_id=server_id, data=data, current_user=current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ServerService = Depends(get_server_service),
):
    try:
        await service.delete(server_id=server_id, current_user=current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc