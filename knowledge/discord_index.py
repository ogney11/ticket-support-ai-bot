from sqlalchemy.ext.asyncio import AsyncSession
from database.repositories.knowledge_index import KnowledgeIndexRepository


class DiscordIndexSearch:
    @staticmethod
    async def search(session: AsyncSession, query: str, limit: int = 3):
        return await KnowledgeIndexRepository.search(session, query, limit)
