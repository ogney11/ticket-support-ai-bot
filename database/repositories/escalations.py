from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Escalation
from datetime import datetime


class EscalationRepository:
    @staticmethod
    async def create(
        session: AsyncSession, ticket_id: int, reason: str | None = None
    ) -> Escalation:
        record = Escalation(ticket_id=ticket_id, reason=reason)
        session.add(record)
        await session.commit()
        return record

    @staticmethod
    async def get_last_for_ticket(session: AsyncSession, ticket_id: int):
        stmt = (
            select(Escalation)
            .where(
                Escalation.ticket_id == ticket_id,
                Escalation.resolved == False,
            )
            .order_by(Escalation.triggered_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_last_notified(session: AsyncSession, ticket_id: int):
        stmt = (
            update(Escalation)
            .where(
                Escalation.ticket_id == ticket_id,
                Escalation.resolved == False,
            )
            .values(last_notified=datetime.utcnow())
        )
        await session.execute(stmt)
        await session.commit()

    @staticmethod
    async def mark_resolved(session: AsyncSession, escalation_id: int):
        escalation = await session.get(Escalation, escalation_id)
        if escalation:
            escalation.resolved = True
            await session.commit()
        return escalation

    @staticmethod
    async def list_open_for_ticket(session: AsyncSession, ticket_id: int):
        stmt = (
            select(Escalation)
            .where(
                Escalation.ticket_id == ticket_id,
                Escalation.resolved == False,
            )
            .order_by(Escalation.triggered_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
