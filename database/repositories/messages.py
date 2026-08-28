from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import TicketMessage, Ticket
from datetime import datetime


class MessageRepository:
    @staticmethod
    async def create(
        session: AsyncSession, ticket_id: int, message
    ) -> TicketMessage:
        record = TicketMessage(
            ticket_id=ticket_id,
            discord_message_id=message.id,
            author_id=message.author.id,
            author_type="user",
            content=message.content or "",
            created_at=message.created_at.replace(tzinfo=None)
            if message.created_at
            else datetime.utcnow(),
        )
        session.add(record)
        await session.commit()
        return record

    @staticmethod
    async def create_bot(
        session: AsyncSession, ticket_id: int, content: str, discord_message_id: int
    ) -> TicketMessage:
        record = TicketMessage(
            ticket_id=ticket_id,
            discord_message_id=discord_message_id,
            author_id=0,
            author_type="bot",
            content=content,
        )
        session.add(record)
        await session.commit()
        return record

    @staticmethod
    async def get_recent(
        session: AsyncSession, ticket_id: int, limit: int = 10
    ):
        stmt = (
            select(TicketMessage)
            .where(TicketMessage.ticket_id == ticket_id)
            .order_by(TicketMessage.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return list(reversed(rows))

    @staticmethod
    async def get_by_discord_id(session: AsyncSession, discord_message_id: int):
        stmt = select(TicketMessage).where(
            TicketMessage.discord_message_id == discord_message_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def count_by_ticket(session: AsyncSession, ticket_id: int) -> int:
        stmt = select(TicketMessage).where(TicketMessage.ticket_id == ticket_id)
        result = await session.execute(stmt)
        return len(result.scalars().all())
