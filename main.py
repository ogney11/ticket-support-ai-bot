import asyncio

import discord
from discord.ext import commands

from config import Config
from database.connection import close_db, init_db
from support.knowledge_commands import KnowledgeCommands
from support.knowledge_listener import KnowledgeListener
from support.message_handler import MessageHandler
from utils.logging import logger, setup_logging

setup_logging(level=Config.LOG_LEVEL)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)


async def _run_backfill():
    from knowledge.backfill import backfill_channels

    try:
        summary = await backfill_channels(
            bot,
            channel_ids=Config.KNOWLEDGE_BACKFILL_CHANNELS or None,
            limit=Config.KNOWLEDGE_BACKFILL_LIMIT,
        )
        logger.info(summary)
    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (id: {bot.user.id})")
    await init_db()
    try:
        await bot.tree.sync()
        logger.info("Slash commands synced")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")
    if Config.KNOWLEDGE_BACKFILL:
        asyncio.get_running_loop().create_task(_run_backfill())


async def main():
    Config.validate()
    await bot.add_cog(MessageHandler(bot))
    await bot.add_cog(KnowledgeListener(bot))
    await bot.add_cog(KnowledgeCommands(bot))
    try:
        async with bot:
            await bot.start(Config.DISCORD_TOKEN)
    finally:
        await close_db()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
