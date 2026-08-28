import asyncio

import discord

from ai.groq_client import GroqClient
from config import Config
from database.connection import async_session
from database.repositories.knowledge_index import KnowledgeIndexRepository
from utils.logging import logger
from support.knowledge_listener import KnowledgeListener
from support.ticket_detector import TicketDetector

BACKFILL_BATCH = 50


async def _channel_eligible(channel) -> bool:
    if not isinstance(channel, discord.TextChannel):
        return False
    if Config.KNOWLEDGE_CHANNEL_IDS:
        return channel.id in Config.KNOWLEDGE_CHANNEL_IDS
    if Config.KNOWLEDGE_INDEX_ALL:
        if TicketDetector.is_ticket(channel):
            return False
        if channel.id in Config.KNOWLEDGE_BLACKLIST_IDS:
            return False
        return True
    return False


async def _collect_channel_history(channel, limit: int) -> list[dict]:
    """Pull up to `limit` recent messages from a channel and return rows."""
    rows = []
    count = 0
    async for message in channel.history(limit=limit):
        if message.author.bot:
            continue
        content = (message.content or "").strip()
        if not content:
            continue
        if Config.KNOWLEDGE_AI_FILTER and not KnowledgeListener._cheap_filter(content):
            continue
        rows.append(
            {
                "channel_id": channel.id,
                "message_id": message.id,
                "author_id": message.author.id,
                "content": content,
            }
        )
        count += 1
    return rows


async def _store_batch(groq: GroqClient, rows: list[dict]) -> int:
    """Optionally AI-filter the batch, then bulk insert. Returns inserted count."""
    kept = []
    if Config.KNOWLEDGE_AI_FILTER:
        for r in rows:
            try:
                if await groq.is_useful_knowledge(r["content"]):
                    kept.append(r)
            except Exception as e:
                logger.error(f"Backfill AI filter error: {e}")
    else:
        kept = rows
    if not kept:
        return 0
    async with async_session() as session:
        inserted = await KnowledgeIndexRepository.bulk_create(session, kept)
    return inserted


async def backfill_channels(bot, channel_ids: list[int] | None = None, limit: int = 200):
    """Scan eligible channels (or the given ones) and index their history.

    Returns a summary string of how many messages were indexed.
    """
    if not bot.user:
        return "Backfill skipped: bot not ready."

    channels = []
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel_ids is not None and channel.id not in channel_ids:
                continue
            if await _channel_eligible(channel):
                channels.append(channel)

    groq = GroqClient()
    total_indexed = 0
    total_scanned = 0
    for channel in channels:
        try:
            rows = await _collect_channel_history(channel, limit)
            total_scanned += len(rows)
            if not rows:
                continue
            inserted = await _store_batch(groq, rows)
            total_indexed += inserted
            logger.info(
                f"Backfilled #{channel.name}: scanned {len(rows)}, "
                f"indexed {inserted}"
            )
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Backfill failed for #{channel.name}: {e}")

    return (
        f"Backfill done: scanned {total_scanned} candidate messages, "
        f"indexed {total_indexed} as knowledge."
    )
