from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import KnowledgeEntry
from sqlalchemy import delete as sa_delete


class KnowledgeRepository:
    @staticmethod
    async def search(
        session: AsyncSession, query: str, limit: int = 5
    ) -> list[KnowledgeEntry]:
        stmt = (
            select(KnowledgeEntry)
            .where(
                and_(
                    KnowledgeEntry.active == True,
                    or_(
                        KnowledgeEntry.question.like(f"%{query}%"),
                        KnowledgeEntry.answer.like(f"%{query}%"),
                        KnowledgeEntry.keywords.like(f"%{query}%"),
                    ),
                )
            )
            .order_by(KnowledgeEntry.priority.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, entry_id: int):
        return await session.get(KnowledgeEntry, entry_id)

    @staticmethod
    async def create(
        session: AsyncSession,
        question: str,
        answer: str,
        keywords: str | None = None,
        category: str | None = None,
        priority: int = 0,
    ) -> KnowledgeEntry:
        entry = KnowledgeEntry(
            question=question,
            answer=answer,
            keywords=keywords,
            category=category,
            source="manual",
            priority=priority,
            active=True,
        )
        session.add(entry)
        await session.commit()
        return entry

    @staticmethod
    async def update(
        session: AsyncSession,
        entry_id: int,
        question: str | None = None,
        answer: str | None = None,
        keywords: str | None = None,
        category: str | None = None,
        priority: int | None = None,
        active: bool | None = None,
    ) -> KnowledgeEntry | None:
        entry = await session.get(KnowledgeEntry, entry_id)
        if not entry:
            return None
        if question is not None:
            entry.question = question
        if answer is not None:
            entry.answer = answer
        if keywords is not None:
            entry.keywords = keywords
        if category is not None:
            entry.category = category
        if priority is not None:
            entry.priority = priority
        if active is not None:
            entry.active = active
        await session.commit()
        return entry

    @staticmethod
    async def delete(session: AsyncSession, entry_id: int) -> bool:
        result = await session.execute(
            sa_delete(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
        )
        await session.commit()
        return result.rowcount > 0

    @staticmethod
    async def list_all(
        session: AsyncSession, limit: int = 100, offset: int = 0
    ) -> list[KnowledgeEntry]:
        stmt = (
            select(KnowledgeEntry)
            .order_by(KnowledgeEntry.priority.desc(), KnowledgeEntry.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def count(session: AsyncSession) -> int:
        stmt = select(KnowledgeEntry)
        result = await session.execute(stmt)
        return len(result.scalars().all())
