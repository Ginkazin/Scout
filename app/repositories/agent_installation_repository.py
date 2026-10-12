from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_installation import AgentInstallation
from app.repositories.base_repository import BaseRepository


class AgentInstallationRepository(BaseRepository[AgentInstallation]):
    def __init__(self, db: AsyncSession):
        super().__init__(AgentInstallation, db)

    # Retorna o ID do agente associado ao hash do código de instalação, se existir.
    async def get_agent_id_by_code_hash(
        self,
        code_hash: str,
    ) -> UUID | None:
        statement = select(AgentInstallation.agent_id).where(
            AgentInstallation.code_hash == code_hash,
        )

        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    # Verifica se o código de instalação ainda é válido e não foi consumido.
    async def replace_code(
        self,
        agent_id: UUID,
        code_hash: str,
        expires_in_seconds: int,
    ) -> AgentInstallation:
        """Cria ou substitui o código de instalação do agente."""
        if expires_in_seconds <= 0:
            raise ValueError("A validade deve ser maior que zero")

        validity = timedelta(seconds=expires_in_seconds)

        statement = (
            insert(AgentInstallation)
            .values(
                agent_id=agent_id,
                code_hash=code_hash,
                expires_at=func.clock_timestamp() + validity,
                consumed_at=None,
            )
            .on_conflict_do_update(
                index_elements=[AgentInstallation.agent_id],
                set_={
                    "code_hash": code_hash,
                    "expires_at": func.clock_timestamp() + validity,
                    "consumed_at": None,
                    "updated_at": func.clock_timestamp(),
                },
            )
            .returning(AgentInstallation)
            .execution_options(populate_existing=True)
        )

        result = await self.db.execute(statement)
        return result.scalar_one()

    # Consome o código de instalação, marcando-o como consumido se ainda estiver válido e disponível.
    async def consume_code(
        self,
        agent_id: UUID,
        code_hash: str,
    ) -> bool:
        """Consome o código somente se ainda estiver válido e disponível."""
        statement = (
            update(AgentInstallation)
            .where(
                AgentInstallation.agent_id == agent_id,
                AgentInstallation.code_hash == code_hash,
                AgentInstallation.consumed_at.is_(None),
                AgentInstallation.expires_at > func.clock_timestamp(),
            )
            .values(
                consumed_at=func.clock_timestamp(),
                updated_at=func.clock_timestamp(),
            )
            .returning(AgentInstallation.id)
            .execution_options(synchronize_session=False)
        )

        result = await self.db.execute(statement)
        return result.scalar_one_or_none() is not None