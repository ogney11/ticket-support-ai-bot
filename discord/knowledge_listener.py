import discord
from discord.ext import commands

from config import Config
from database.connection import async_session
from database.repositories.knowledge_index import KnowledgeIndexRepository
from utils.logging import logger


class KnowledgeListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id not in Config.KNOWLEDGE_CHANNEL_IDS:
            return
        content = (message.content or "").strip()
        if not content:
            return
        try:
            async with async_session() as session:
                existing = await KnowledgeIndexRepository.get_by_message_id(
                    session, message.id
                )
                if existing:
                    return
                await KnowledgeIndexRepository.create(
                    session,
                    channel_id=message.channel.id,
                    message_id=message.id,
                    author_id=message.author.id,
                    content=content,
                )
        except Exception as e:
            logger.error(f"Knowledge indexing failed: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.channel.id not in Config.KNOWLEDGE_CHANNEL_IDS:
            return
        try:
            async with async_session() as session:
                await KnowledgeIndexRepository.delete_by_message_id(session, message.id)
        except Exception as e:
            logger.error(f"Knowledge delete failed: {e}", exc_info=True)
