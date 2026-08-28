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


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (id: {bot.user.id})")
    await init_db()


async def main():
    Config.validate()
    await bot.add_cog(MessageHandler(bot))
    await bot.add_cog(KnowledgeListener(bot))
    await bot.add_cog(KnowledgeCommands(bot))
    try:
        async with bot:
            if hasattr(bot, "tree"):
                await bot.tree.sync()
            await bot.start(Config.DISCORD_TOKEN)
    finally:
        await close_db()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
