import re
from datetime import datetime, timedelta

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
    r"^(hi+|hello+|hej+|hey+|yo|sup|cze|czesc|cześć|good|ok|okay|ok+|bye|"
    r"thanks|thank you|ty|thx|dziękuj|dzieki|dziekuje|dzk|dzkuje|"
    r"👍|👋|🙂|😊|😃|🙏|❤|💖)[!.?\s]*$",
    re.I,
)

NOISE_RE = re.compile(
    r"^(hi+|hello+|hej+|hey+|yo|sup|cze|czesc|cześć|good|ok|okay|ok+|bye|"
    r"thanks|thank you|ty|thx|dziękuj|dzieki|dziekuje|dzk|dzkuje|"
    r"👍|👋|🙂|😊|😃|🙏|❤|💖)[!.?\s]*$",
    re.I,
)

# Explicit requests to involve a human/staff member.
STAFF_REQUEST_RE = re.compile(
    r"(\bstaff\b|"
    r"\bmoderator\b|"
    r"\bmod\b|"
    r"\badmin\w*\b|"
    r"\bsupport team\b|"
    r"\bsupport agent\b|"
    r"\bsupport\b|"
    r"\bhuman\b|"
    r"\bperson\b|"
    r"\bczłowieka\b|"
    r"\bczłowiek\b|"
    r"\bpracownika\b|"
    r"\bpracownik\b|"
    r"\badministratora\b|"
    r"\badministrator\b|"
    r"\bmoderator\w*\b|"
    r"\bmoderatorem\b|"
    r"\bmoderację\b|"
    r"\bmoderacji\b|"
    r"\bmoderacja\b|"
    r"\bmoderatorzy\b|"
    r"\bzespołu wsparcia\b|"
    r"\bzespół wsparcia\b|"
    r"\bsupportu\b)",
    re.I,
)

GREETING = (
    "Hello! 👋 Welcome to our support ticket. I'm the AI assistant here to help you. "
    "Please tell me what you need help with and I'll do my best to assist you."
)

NO_KNOWLEDGE_RESPONSE = (
    "I don't have enough information to answer that yet. "
    "Could you provide a bit more detail about your issue?"
)


class MessageHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.groq = GroqClient()
        self.retriever = KnowledgeRetriever()
        self.escalation_manager = EscalationManager()
        self.rate_limiter = RateLimiter(
            per_user=Config.RATE_LIMIT_PER_USER,
            per_ticket=Config.RATE_LIMIT_PER_TICKET,
            window=Config.RATE_LIMIT_WINDOW,
        )

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

        is_staff = self._is_staff(message.author, message.guild)

        if is_staff:
            async with async_session() as session:
                await TicketRepository.mark_staff_message(session, ticket.id)
            return

        # Staff handover: if a staff member has recently written, the bot stays
        # quiet unless @mentioned or the staff timeout has elapsed.
        if ticket.bot_paused:
            resumed = self._bot_mentioned(message)
            if not resumed and ticket.last_staff_message_at:
                elapsed = datetime.utcnow() - ticket.last_staff_message_at
                if elapsed >= timedelta(minutes=Config.STAFF_TIMEOUT_MINUTES):
                    resumed = True
            if resumed:
                async with async_session() as session:
                    await TicketRepository.resume_bot(session, ticket.id)
            else:
                return

        if GREETING_RE.match(content):
            await self._handle_greeting(ticket, message)
            return

        # Explicit staff request: involve a human immediately (with cooldown).
        if STAFF_REQUEST_RE.search(content):
            async with async_session() as session:
                await self.escalation_manager.trigger(
                    session,
                    ticket.id,
                    message.channel,
                    message.guild,
                    reason="User explicitly requested staff",
                )
            return

        await self._handle_support(ticket, message)

    async def _handle_greeting(self, ticket, message: discord.Message):
        reply = (
            "Hello! 😊 How can I help you today? "
            "Tell me your issue and I'll do my best to assist."
        )
        try:
            greeting_context = build_context(
                system=(
                    "You are a friendly Discord support assistant. The user just said "
                    "a casual greeting. Reply briefly and warmly in the SAME language as "
                    "the user's message, then ask how you can help. Do not mention staff. "
                    'Reply with a JSON object: {"action":"answer","response":"..."}.'
                ),
                knowledge=[],
                history=[],
                user_message=message.content,
            )
            result, _ = await self.groq.generate(greeting_context)
            if result.action in ("answer", "ask_more") and result.response:
                reply = result.response
        except Exception as e:
            logger.error(f"Greeting AI failed, using fallback: {e}")
        try:
            sent = await message.channel.send(reply)
            async with async_session() as session:
                await MessageRepository.create_bot(session, ticket.id, reply, sent.id)
        except Exception as e:
            logger.error(f"Greeting reply failed: {e}", exc_info=True)

    def _is_staff(self, author, guild) -> bool:
        if not guild:
            return False
        if Config.SUPPORT_ROLE_ID == 0:
            return False
        role = guild.get_role(Config.SUPPORT_ROLE_ID)
        return role is not None and role in author.roles

    def _bot_mentioned(self, message) -> bool:
        return self.bot.user is not None and self.bot.user in message.mentions

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
            try:
                await message.channel.send(
                    "Sorry, I ran into a temporary issue. Could you try again in a moment?"
                )
            except Exception as send_err:
                logger.error(f"Fallback send failed: {send_err}", exc_info=True)
            async with async_session() as session:
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
                    reason=result.reason or "AI chose to escalate",
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

        # "ask_more" and "answer" both send a normal reply - never ping staff.
        if not result.response or not self._validate_response(result.response):
            reply = result.response or NO_KNOWLEDGE_RESPONSE
            try:
                sent = await message.channel.send(reply)
                async with async_session() as session:
                    await MessageRepository.create_bot(
                        session, ticket.id, reply, sent.id
                    )
                    await UsageLogRepository.create(
                        session,
                        ticket_id=ticket.id,
                        user_message_id=message.id,
                        response=reply,
                        success=True,
                        model=self.groq.model,
                        tokens_used=tokens,
                    )
            except Exception as e:
                logger.error(f"Sending fallback message failed: {e}", exc_info=True)
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
