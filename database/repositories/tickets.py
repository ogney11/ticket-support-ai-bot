from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Ticket
from datetime import datetime


class TicketRepository:
    @staticmethod
    async def get_by_id(session: AsyncSession, ticket_id: int):
        return await session.get(Ticket, ticket_id)

    @staticmethod
    async def get_by_channel(session: AsyncSession, channel_id: int):
        stmt = select(Ticket).where(Ticket.channel_id == channel_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def mark_staff_message(session: AsyncSession, ticket_id: int):
        ticket = await session.get(Ticket, ticket_id)
        if ticket:
            ticket.bot_paused = True
            ticket.last_staff_message_at = datetime.utcnow()
            await session.commit()
        return ticket

    @staticmethod
    async def resume_bot(session: AsyncSession, ticket_id: int):
        ticket = await session.get(Ticket, ticket_id)
        if ticket:
            ticket.bot_paused = False
            await session.commit()
        return ticket

    @staticmethod
    async def create(
        session: AsyncSession,
        ticket_id: int,
        channel_id: int,
        guild_id: int,
        creator_id: int,
    ):
        ticket = Ticket(
            id=ticket_id,
            channel_id=channel_id,
            guild_id=guild_id,
            creator_id=creator_id,
        )
        session.add(ticket)
        await session.commit()
        return ticket

    @staticmethod
    async def create_if_missing(
        session: AsyncSession, channel_id: int, guild_id: int, creator_id: int
    ):
        ticket = await TicketRepository.get_by_channel(session, channel_id)
        if ticket:
            return ticket
        # Deterministic id = channel_id (channel ids are unique per guild)
        ticket = Ticket(
            id=channel_id,
            channel_id=channel_id,
            guild_id=guild_id,
            creator_id=creator_id,
        )
        session.add(ticket)
        await session.commit()
        return ticket

    @staticmethod
    async def close(session: AsyncSession, ticket_id: int):
        ticket = await session.get(Ticket, ticket_id)
        if ticket:
            ticket.is_open = False
            await session.commit()
        return ticket

    @staticmethod
    async def list_by_guild(session: AsyncSession, guild_id: int, limit: int = 100):
        stmt = (
            select(Ticket)
            .where(Ticket.guild_id == guild_id)
            .order_by(Ticket.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
