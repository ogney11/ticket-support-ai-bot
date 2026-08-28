from sqlalchemy.ext.asyncio import AsyncSession
from database.repositories.knowledge import KnowledgeRepository


class DatabaseKnowledgeSearch:
    @staticmethod
    async def search(session: AsyncSession, query: str, limit: int = 5):
        return await KnowledgeRepository.search(session, query, limit)
