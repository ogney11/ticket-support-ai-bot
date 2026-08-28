import discord
from discord.ext import commands

from config import Config
from database.connection import async_session
from database.repositories.knowledge_index import KnowledgeIndexRepository
from utils.logging import logger

from .ticket_detector import TicketDetector


class KnowledgeListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _should_index(channel) -> bool:
        """Decide whether a channel should be indexed as knowledge."""
        # Never index DMs / non-text.
        if not isinstance(channel, discord.TextChannel):
            return False
        # Whitelist mode.
        if Config.KNOWLEDGE_CHANNEL_IDS:
            return channel.id in Config.KNOWLEDGE_CHANNEL_IDS
        # Index-all mode: skip blacklist + all ticket channels.
        if Config.KNOWLEDGE_INDEX_ALL:
            if TicketDetector.is_ticket(channel):
                return False
            if channel.id in Config.KNOWLEDGE_BLACKLIST_IDS:
                return False
            return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not self._should_index(message.channel):
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
        if not self._should_index(message.channel):
            return
        try:
            async with async_session() as session:
                await KnowledgeIndexRepository.delete_by_message_id(session, message.id)
        except Exception as e:
            logger.error(f"Knowledge delete failed: {e}", exc_info=True)
