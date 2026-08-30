from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer_schema import (
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
    )
from app.services.customer_service import CustomerService
from app.api.dependencies import get_customer_service

router = APIRouter(prefix="/customers", tags=["customers"])

# Endpoint para criar um novo cliente.
@router.post("",response_model=CustomerResponse, status_code=status.HTTP_201_CREATED,)
async def create_customer(
    data: CustomerCreate,
    current_user: User = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
):
    try:
        return await service.create(
            data=data,
            current_user=current_user,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

# Endpoint para listar clientes do usuário atual com paginação.
@router.get("", response_model=list[CustomerResponse],)
async def list_customer(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100,),
    current_user: User = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
):
    return await service.list(
        current_user=current_user,
        skip=skip,
        limit=limit,
    )

# Endpoint para obter um cliente pelo ID e pelo usuário atual.
@router.get("/{customer_id}", response_model= CustomerResponse,)    
async def get_customer(
    customer_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
):
    try:
        return await service.get_by_id(
            customer_id=customer_id,
            current_user=current_user,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        ) from exc

# Endpoint para atualizar um cliente existente.
@router.patch("/{customer_id}", response_model=CustomerResponse,)
async def update_customer(
    customer_id: UUID,
    data: CustomerUpdate,
    current_user: User = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
):
    try:
        return await service.update(
            customer_id=customer_id,
            data= data,
            current_user=current_user,
        )
    except ValueError as exc:
        message = str(exc)

        if message == "Cliente não encontrado":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado",
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        ) from exc

# Endpoint para deletar um cliente existente.
@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT,)
async def delete_customer(
    customer_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
):
    try:
        await service.delete(
            customer_id=customer_id,
            current_user=current_user
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        ) from exc