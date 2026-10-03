from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies import (
    get_agent_service,
    get_agent_token,
    get_current_user,
)
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from app.models.user import User
from app.schemas.agent_schema import (
    AgentCreateResponse,
    AgentHeartbeat,
    AgentResponse,
    AgentCreate,
    AgentRuntimeConfig
)
from app.services.agent_service import AgentService


router = APIRouter(tags=["agents"])

# Rota para criar um novo agente associado a um servidor, garantindo que o servidor pertença ao usuário atual.
@router.post(
    "/servers/{server_id}/agent",
    response_model=AgentCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_agent(
    server_id: UUID,
    data: AgentCreate,
    response: Response,
    current_user: User = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
):
    try:
        agent, token = await service.create(
            server_id=server_id,
            current_user=current_user,
            data=data,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    response.headers["Cache-Control"] = "no-store"

    agent_data = AgentResponse.model_validate(agent)

    return AgentCreateResponse(
        **agent_data.model_dump(),
        token=token,
    )

# Rota para obter informações de um agente específico, garantindo que ele pertença ao usuário atual.
@router.get(
    "/agents/{agent_id}",
    response_model=AgentResponse,
)
async def get_agent(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
):
    try:
        return await service.get_by_id(
            agent_id=agent_id,
            current_user=current_user,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

# Rota para habilitar um agente que estava desativado, alterando seu status para PENDING.
@router.post(
    "/agents/{agent_id}/disable",
    response_model=AgentResponse,
)
async def disable_agent(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
):
    try:
        return await service.disable(
            agent_id=agent_id,
            current_user=current_user,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

# Rota para habilitar um agente que estava desativado, alterando seu status para PENDING.
@router.post(
    "/agents/{agent_id}/enable",
    response_model=AgentResponse,
)
async def enable_agent(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
):
    try:
        return await service.enable(
            agent_id=agent_id,
            current_user=current_user,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

# Rota para o heartbeat do agente, que atualiza o status do agente no sistema.  
@router.post(
    "/agent/heartbeat",
    response_model=AgentResponse,
)
async def agent_heartbeat(
    data: AgentHeartbeat,
    token: str = Depends(get_agent_token),
    service: AgentService = Depends(get_agent_service),
):
    try:
        return await service.heartbeat(
            token=token,
            data=data,
        )
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

# Rota para deletar um agente, garantindo que ele pertença ao usuário atual.
@router.delete(
    "/agents/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_agent(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
):
    try:
        await service.delete(
            agent_id=agent_id,
            current_user=current_user,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

@router.get(
    "/agent/config",
    response_model=AgentRuntimeConfig,
)
async def get_agent_config(
    response: Response,
    token: str = Depends(get_agent_token),
    service: AgentService = Depends(get_agent_service),
):
    response.headers["Cache-Control"] = "no-store"

    try:
        return await service.get_runtime_config(token)
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc