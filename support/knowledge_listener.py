import discord
from discord.ext import commands

from ai.groq_client import GroqClient
from config import Config
from database.connection import async_session
from database.repositories.knowledge_index import KnowledgeIndexRepository
from utils.logging import logger

from .ticket_detector import TicketDetector


class KnowledgeListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.groq = GroqClient()

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

    @staticmethod
    def _cheap_filter(content: str) -> bool:
        """Fast heuristic pre-filter to avoid paying for obvious non-knowledge."""
        if len(content) < 20:
            return False
        lower = content.lower()
        casual = (
            "lol", "lmao", "xd", "fr", "ngl", "omg", "wow", "nice",
            "cool", "same", "agree", "yeah", "yess", "no way", "haha",
        )
        if any(token in lower for token in casual):
            return False
        # Lots of emojis / punctuation-only noise.
        letters = sum(c.isalpha() for c in content)
        if letters < 8:
            return False
        return True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not self._should_index(message.channel):
            return
        content = (message.content or "").strip()
        if not content:
            return
        if Config.KNOWLEDGE_AI_FILTER and not self._cheap_filter(content):
            return
        try:
            if Config.KNOWLEDGE_AI_FILTER:
                useful = await self.groq.is_useful_knowledge(content)
                if not useful:
                    return
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
