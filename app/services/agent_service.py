from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from app.core.agent_security import generate_agent_token, parse_agent_token, verify_agent_secret
from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.models.agent import Agent, AgentStatus
from app.models.user import User
from app.repositories.agent_repository import AgentRepository
from app.repositories.server_repository import ServerRepository
from app.schemas.agent_schema import AgentHeartbeat


class AgentService:
    def __init__(
        self,
        agent_repository: AgentRepository,
        server_repository: ServerRepository,
    ):
        self.agent_repository = agent_repository
        self.server_repository = server_repository

    # Método para criar um novo agente associado a um servidor.
    async def create(
        self,
        server_id: UUID,
        current_user: User,
    ) -> tuple[Agent, str]:
        # Confirma que o servidor pertence ao usuário.
        server = await self.server_repository.get_by_id_and_user_id(
            server_id=server_id,
            user_id=current_user.id,
        )

        if server is None:
            raise NotFoundError("Servidor não encontrado")

        # Cada servidor pode possuir apenas um Agent.
        existing_agent = await self.agent_repository.get_by_server_id(
            server_id
        )

        if existing_agent is not None:
            raise ConflictError("Este servidor já possui um agente")

        # O UUID precisa existir antes da geração do token.
        agent_id = uuid4()
        token, token_hash = generate_agent_token(agent_id)

        agent = Agent(
            id=agent_id,
            server_id=server.id,
            token_hash=token_hash,
            status=AgentStatus.PENDING,
            auto_update=False,
        )

        try:
            agent = await self.agent_repository.create(agent)
        except IntegrityError as exc:
            raise ConflictError(
                "Não foi possível criar o agente por conflito de dados"
            ) from exc

        # Somente o hash é persistido. O token será entregue na criação.
        return agent, token

    # Método para obter um agente pelo ID, garantindo que ele pertença ao usuário atual.
    async def get_by_id(
        self,
        agent_id: UUID,
        current_user: User,
    ) -> Agent:
        agent = await self.agent_repository.get_by_id_and_user_id(
            agent_id=agent_id,
            user_id=current_user.id,
        )

        if agent is None:
            raise NotFoundError("Agente não encontrado")

        return agent

    # Método para desativar um agente.
    async def disable(
        self,
        agent_id: UUID,
        current_user: User,
    ) -> Agent:
        agent = await self.get_by_id(agent_id, current_user)

        if agent.status == AgentStatus.DISABLED:
            return agent

        agent.status = AgentStatus.DISABLED
        return await self.agent_repository.update(agent)

    # Método para habilitar um agente que estava desativado, alterando seu status para PENDING.
    async def enable(
        self,
        agent_id: UUID,
        current_user: User,
    ) -> Agent:
        agent = await self.get_by_id(agent_id, current_user)

        if agent.status != AgentStatus.DISABLED:
            raise ConflictError("Agente não está desativado")

        agent.status = AgentStatus.PENDING
        return await self.agent_repository.update(agent)

    # Método para autenticar um agente usando seu token.
    async def authenticate(
        self,
        token: str,
    ) -> Agent:
        error_message = "Token de agente inválido"

        try:
            agent_id, secret = parse_agent_token(token)
        except ValueError as exc:
            raise UnauthorizedError(error_message) from exc

        agent = await self.agent_repository.get_by_id(agent_id)

        if agent is None:
            raise UnauthorizedError(error_message)

        if not verify_agent_secret(secret, agent.token_hash):
            raise UnauthorizedError(error_message)

        if agent.status not in (AgentStatus.PENDING, AgentStatus.ONLINE, AgentStatus.OFFLINE):
            raise UnauthorizedError(error_message)

        return agent

    # Método para registrar o heartbeat de um agente, atualizando seu status e versão.
    async def heartbeat(
        self,
        token: str,
        data: AgentHeartbeat,
    ) -> Agent:
        agent = await self.authenticate(token)

        updated_agent = await self.agent_repository.record_heartbeat(
            agent_id=agent.id,
            token_hash=agent.token_hash,
            version=data.version,
        )

        if updated_agent is None:
            raise UnauthorizedError("Credenciais de agente inválidas")

        return updated_agent