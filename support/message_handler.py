import re

import discord
from discord.ext import commands

from ai.groq_client import GroqClient
from ai.prompts import SYSTEM_PROMPT
from ai.context import build_context
from config import Config
from database.connection import async_session
from database.repositories.messages import MessageRepository
from database.repositories.tickets import TicketRepository
from database.repositories.usage_logs import UsageLogRepository
from escalation import EscalationManager
from knowledge.retrieval import KnowledgeRetriever
from utils.logging import logger
from utils.rate_limit import RateLimiter

GREETING_RE = re.compile(
    r"^(hi|hello|hey|sup|yo|ok|okay|thanks|thank you|ty|thx)[!.\s]*$", re.I
)

GREETING = (
    "Hello! 👋 Welcome to our support ticket. I'm the AI assistant here to help you. "
    "Please tell me what you need help with and I'll do my best to assist you."
)


class MessageHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.groq = GroqClient()
        self.retriever = KnowledgeRetriever()
        self.escalation_manager = EscalationManager()
        self.rate_limiter = RateLimiter()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not isinstance(message.channel, discord.TextChannel):
            return

        from .ticket_detector import TicketDetector

        if not TicketDetector.is_ticket(message.channel):
            return

        content = (message.content or "").strip()
        if not content:
            return

        async with async_session() as session:
            ticket = await TicketRepository.create_if_missing(
                session,
                channel_id=message.channel.id,
                guild_id=message.guild.id,
                creator_id=message.author.id,
            )
            await MessageRepository.create(session, ticket.id, message)

        if not self.rate_limiter.allow(message.author.id, message.channel.id):
            await message.channel.send(
                "You're sending messages too quickly. Please slow down."
            )
            return

        if GREETING_RE.match(content):
            return

        await self._handle_support(ticket, message)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        from .ticket_detector import TicketDetector

        if not isinstance(channel, discord.TextChannel):
            return
        if not TicketDetector.is_ticket(channel):
            return
        try:
            sent = await channel.send(GREETING)
            async with async_session() as session:
                ticket = await TicketRepository.create_if_missing(
                    session,
                    channel_id=channel.id,
                    guild_id=channel.guild.id,
                    creator_id=0,
                )
                await MessageRepository.create_bot(
                    session, ticket.id, GREETING, sent.id
                )
        except Exception as e:
            logger.error(f"Auto-greet failed in {channel.id}: {e}", exc_info=True)

    async def _handle_support(self, ticket, message: discord.Message):
        try:
            async with async_session() as session:
                history = await MessageRepository.get_recent(
                    session, ticket.id, limit=Config.HISTORY_LIMIT
                )
                db_knowledge = await self.retriever.search_database(
                    session, message.content
                )
                index_knowledge = await self.retriever.search_discord_index(
                    session, message.content
                )
                combined = list(db_knowledge) + list(index_knowledge)

                if not combined:
                    await self.escalation_manager.trigger(
                        session,
                        ticket.id,
                        message.channel,
                        message.guild,
                        reason="No knowledge match",
                    )
                    return

                context = build_context(
                    system=SYSTEM_PROMPT,
                    knowledge=combined,
                    history=history,
                    user_message=message.content,
                )
        except Exception as e:
            logger.error(f"Context build error: {e}", exc_info=True)
            async with async_session() as session:
                await self.escalation_manager.trigger(
                    session, ticket.id, message.channel, message.guild, reason="error"
                )
            return

        try:
            result, tokens = await self.groq.generate(context)
        except Exception as e:
            logger.error(f"Groq error: {e}", exc_info=True)
            async with async_session() as session:
                await self.escalation_manager.trigger(
                    session, ticket.id, message.channel, message.guild, reason="ai_error"
                )
                await UsageLogRepository.create(
                    session,
                    ticket_id=ticket.id,
                    user_message_id=message.id,
                    success=False,
                    error=str(e),
                    model=self.groq.model,
                )
            return

        if result.action == "escalate":
            async with async_session() as session:
                await self.escalation_manager.trigger(
                    session,
                    ticket.id,
                    message.channel,
                    message.guild,
                    reason="AI chose to escalate",
                )
                await UsageLogRepository.create(
                    session,
                    ticket_id=ticket.id,
                    user_message_id=message.id,
                    response=result.response,
                    success=True,
                    model=self.groq.model,
                    tokens_used=tokens,
                )
            return

        if not self._validate_response(result.response):
            async with async_session() as session:
                await self.escalation_manager.trigger(
                    session,
                    ticket.id,
                    message.channel,
                    message.guild,
                    reason="Unsafe response",
                )
                await UsageLogRepository.create(
                    session,
                    ticket_id=ticket.id,
                    user_message_id=message.id,
                    response=result.response,
                    success=False,
                    error="response validation failed",
                    model=self.groq.model,
                )
            return

        try:
            sent = await message.channel.send(result.response)
            async with async_session() as session:
                await MessageRepository.create_bot(
                    session, ticket.id, result.response, sent.id
                )
                await UsageLogRepository.create(
                    session,
                    ticket_id=ticket.id,
                    user_message_id=message.id,
                    response=result.response,
                    success=True,
                    model=self.groq.model,
                    tokens_used=tokens,
                )
        except Exception as e:
            logger.error(f"Sending message failed: {e}", exc_info=True)

    def _validate_response(self, text: str) -> bool:
        lowered = text.lower()
        blocked = [
            "system prompt",
            "api key",
            "bearer ",
            "your instructions",
            "as an ai",
            "i am an ai",
        ]
        for phrase in blocked:
            if phrase in lowered:
                return False
        if "password" in lowered and ("database" in lowered or "mysql" in lowered):
            return False
        return True
