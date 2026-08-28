from sqlalchemy.ext.asyncio import AsyncSession

from knowledge.database_search import DatabaseKnowledgeSearch
from knowledge.discord_index import DiscordIndexSearch


class KnowledgeRetriever:
    @staticmethod
    async def search_discord_index(session: AsyncSession, query: str, limit: int = 3):
        return await DiscordIndexSearch.search(session, query, limit)

    @staticmethod
    async def search_database(session: AsyncSession, query: str, limit: int = 5):
        return await DatabaseKnowledgeSearch.search(session, query, limit)

    @staticmethod
    async def combined(
        session: AsyncSession,
        query: str,
        db_limit: int = 5,
        index_limit: int = 3,
    ):
        db_knowledge = await DatabaseKnowledgeSearch.search(session, query, db_limit)
        index_knowledge = await DiscordIndexSearch.search(session, query, index_limit)
        return list(db_knowledge) + list(index_knowledge)
