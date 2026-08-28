from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import KnowledgeChannelMessage
from sqlalchemy import delete as sa_delete


class KnowledgeIndexRepository:
    @staticmethod
    async def search(
        session: AsyncSession, query: str, limit: int = 3
    ) -> list[KnowledgeChannelMessage]:
        stmt = (
            select(KnowledgeChannelMessage)
            .where(
                or_(
                    KnowledgeChannelMessage.content.like(f"%{query}%"),
                )
            )
            .order_by(KnowledgeChannelMessage.indexed_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create(
        session: AsyncSession,
        channel_id: int,
        message_id: int,
        author_id: int,
        content: str,
    ) -> KnowledgeChannelMessage:
        record = KnowledgeChannelMessage(
            channel_id=channel_id,
            message_id=message_id,
            author_id=author_id,
            content=content,
        )
        session.add(record)
        await session.commit()
        return record

    @staticmethod
    async def get_by_message_id(session: AsyncSession, message_id: int):
        stmt = select(KnowledgeChannelMessage).where(
            KnowledgeChannelMessage.message_id == message_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_by_message_id(session: AsyncSession, message_id: int) -> bool:
        result = await session.execute(
            sa_delete(KnowledgeChannelMessage).where(
                KnowledgeChannelMessage.message_id == message_id
            )
        )
        await session.commit()
        return result.rowcount > 0

    @staticmethod
    async def list_by_channel(
        session: AsyncSession, channel_id: int, limit: int = 100
    ) -> list[KnowledgeChannelMessage]:
        stmt = (
            select(KnowledgeChannelMessage)
            .where(KnowledgeChannelMessage.channel_id == channel_id)
            .order_by(KnowledgeChannelMessage.indexed_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
