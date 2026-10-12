from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from app.core.agent_installation_security import generate_installation_code, hash_installation_code
from app.repositories.agent_installation_repository import AgentInstallationRepository
from app.core.agent_security import generate_agent_token, parse_agent_token, verify_agent_secret
from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.models.agent import Agent, AgentStatus
from app.models.user import User
from app.repositories.agent_repository import AgentRepository
from app.repositories.server_repository import ServerRepository
from app.schemas.agent_schema import AgentHeartbeat, AgentCreate, AgentRuntimeConfig, AgentActivationRequest, AgentActivationResponse, AgentInstallationCodeResponse

INSTALATION_CODE_TTL_SECONDS = 30 * 60  # 30 minutos em segundos

class AgentService:
    def __init__(
        self,
        agent_repository: AgentRepository,
        server_repository: ServerRepository,
        installation_repository: AgentInstallationRepository
    ):
        self.agent_repository = agent_repository
        self.server_repository = server_repository
        self.installation_repository = installation_repository

    # Método para criar um novo agente associado a um servidor.
    async def create(self,server_id: UUID,current_user: User,data:AgentCreate,) -> tuple[Agent, str]:
        # Confirma que o servidor pertence ao usuário.
        server = await self.server_repository.get_by_id_and_user_id(
            server_id=server_id,
            user_id=current_user.id,
        )

        if server is None:
            raise NotFoundError("Servidor não encontrado")
        if server.os_family is None:
            raise ConflictError("Defina Windows ou Linux no cadastro do servidor.")

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
            agent_type=data.agent_type,
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
    async def get_by_id(self,agent_id: UUID,current_user: User,) -> Agent:
        agent = await self.agent_repository.get_by_id_and_user_id(
            agent_id=agent_id,
            user_id=current_user.id,
        )

        if agent is None:
            raise NotFoundError("Agente não encontrado")

        return agent

    # Método para desativar um agente.
    async def disable(self,agent_id: UUID,current_user: User,) -> Agent:
        agent = await self.get_by_id(agent_id, current_user)

        if agent.status == AgentStatus.DISABLED:
            return agent

        agent.status = AgentStatus.DISABLED
        return await self.agent_repository.update(agent)

    # Método para habilitar um agente que estava desativado, alterando seu status para PENDING.
    async def enable(self,agent_id: UUID,current_user: User,) -> Agent:
        agent = await self.get_by_id(agent_id, current_user)

        if agent.status != AgentStatus.DISABLED:
            raise ConflictError("Agente não está desativado")

        agent.status = AgentStatus.PENDING
        return await self.agent_repository.update(agent)

    # Método para autenticar um agente usando seu token.
    async def authenticate(self,token: str,) -> Agent:
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
    async def heartbeat(self,token: str,data: AgentHeartbeat,) -> Agent:
        agent = await self.authenticate(token)

        updated_agent = await self.agent_repository.record_heartbeat(
            agent_id=agent.id,
            token_hash=agent.token_hash,
            version=data.version,
        )

        if updated_agent is None:
            raise UnauthorizedError("Credenciais de agente inválidas")

        return updated_agent

    # Método para deletar um agente, garantindo que ele pertença ao usuário atual.
    async def delete(self,agent_id: UUID,current_user: User,) -> None:
        agent = await self.get_by_id(agent_id=agent_id, current_user=current_user) 

        await self.agent_repository.delete(agent)

    # Método para obter a configuração de runtime de um agente, incluindo informações do servidor associado.
    async def get_runtime_config(self,token: str,) -> AgentRuntimeConfig:
        agent = await self.authenticate(token)

        server = await self.server_repository.get_by_id(agent.server_id)

        if server is None:
            raise UnauthorizedError("Credenciais de agente inválidas")
        if server.os_family is None:
            raise ConflictError("Defina Windows ou Linux no cadastro do servidor.")

        return AgentRuntimeConfig(
            agent_id=agent.id,
            server_id=server.id,
            agent_type=agent.agent_type,
            server_os_family=server.os_family,
        )

    # Método para emitir um código de instalação para um agente, garantindo que ele pertença ao usuário atual e que o servidor associado tenha o sistema operacional definido.
    async def issue_installation_code(self, agent_id: UUID, current_user: User) -> AgentInstallationCodeResponse:
        agent = await self.get_by_id(agent_id,current_user)

        agent = await self.agent_repository.get_by_id_for_update(agent_id)

        if agent is None:
            raise NotFoundError("Agente não encontrado")

        if agent.status == AgentStatus.DISABLED:
            raise ConflictError("Habilite o agente antes de emitir um código de instalação.")

        server = await self.server_repository.get_by_id_and_user_id(server_id=agent.server_id, user_id=current_user.id)

        if server is None:
            raise NotFoundError("Servidor não encontrado")

        if server.os_family is None:
            raise ConflictError("Defina Windows ou Linux no cadastro do servidor.")

        code, code_hash = generate_installation_code()

        installation = await self.installation_repository.replace_code(agent_id=agent.id, code_hash=code_hash, expires_in_seconds=INSTALATION_CODE_TTL_SECONDS)

        return AgentInstallationCodeResponse(
            agent_id=agent.id,
            installation_code=code,
            expires_at=installation.expires_at,
        )

    # Método para ativar um agente usando um código de instalação, garantindo que o código seja válido e compatível com o sistema operacional do servidor.
    async def activate(self, data: AgentActivationRequest) -> AgentActivationResponse:
        error_message = "Código de instalação inválido ou expirado"

        try:
            code_hash = hash_installation_code(data.installation_code.get_secret_value())
        except ValueError:
            raise UnauthorizedError(error_message) from None

        agent_id = (await self.installation_repository.get_agent_id_by_code_hash(code_hash))

        if agent_id is None:
            raise UnauthorizedError(error_message)

        agent = await self.agent_repository.get_by_id_for_update(agent_id)

        if agent is None or agent.status == AgentStatus.DISABLED:
            raise UnauthorizedError(error_message)

        server = await self.server_repository.get_by_id(agent.server_id)

        if server is None:
            raise UnauthorizedError(error_message)

        consumed = await self.installation_repository.consume_code(agent_id=agent.id, code_hash=code_hash)

        if not consumed:
            raise UnauthorizedError(error_message)

        if server.os_family is None:
            raise ConflictError("Defina Windows ou Linux no cadastro do servidor.")

        if server.os_family != data.os_family:
            raise ConflictError("O código de instalação não é compatível com o sistema operacional do servidor.")

        token, token_hash = generate_agent_token(agent.id)

        agent.token_hash = token_hash
        agent.status = AgentStatus.PENDING
        agent.last_seen_at = None

        agent = await self.agent_repository.update(agent)

        return AgentActivationResponse(
            agent_id=agent.id,
            server_id=server.id,
            agent_type=agent.agent_type,
            server_os_family=server.os_family,
            token=token,
        )