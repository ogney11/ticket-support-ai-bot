import discord
from discord import app_commands
from discord.ext import commands

from config import Config
from database.connection import async_session
from database.repositories.knowledge import KnowledgeRepository
from utils.logging import logger


def is_support():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False
        role = interaction.guild.get_role(Config.SUPPORT_ROLE_ID)
        return role is not None and role in interaction.user.roles

    return app_commands.check(predicate)


class KnowledgeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="knowledge", description="Manage the knowledge base")
    @app_commands.describe(
        action="add, remove, search, list or backfill",
        question="Question (for add/search)",
        answer="Answer (for add)",
        keywords="Comma-separated keywords (optional)",
        category="Category (optional)",
        entry_id="Knowledge entry id (for remove)",
        query="Search query (for search)",
        channel="Channel to backfill (optional)",
    )
    @is_support()
    async def knowledge(
        self,
        interaction: discord.Interaction,
        action: str,
        question: str | None = None,
        answer: str | None = None,
        keywords: str | None = None,
        category: str | None = None,
        entry_id: int | None = None,
        query: str | None = None,
        channel: discord.TextChannel | None = None,
    ):
        action = action.lower()

        if action == "backfill":
            from knowledge.backfill import backfill_channels

            await interaction.response.defer(ephemeral=True)
            target = [channel.id] if channel else None
            summary = await backfill_channels(
                self.bot, channel_ids=target, limit=Config.KNOWLEDGE_BACKFILL_LIMIT
            )
            await interaction.followup.send(summary, ephemeral=True)
            return

        async with async_session() as session:
            if action == "add":
                if not question or not answer:
                    await interaction.response.send_message(
                        "`add` requires question and answer.", ephemeral=True
                    )
                    return
                entry = await KnowledgeRepository.create(
                    session, question=question, answer=answer,
                    keywords=keywords, category=category,
                )
                await interaction.response.send_message(
                    f"Added knowledge entry #{entry.id}."
                )
                return

            if action == "remove":
                if entry_id is None:
                    await interaction.response.send_message(
                        "`remove` requires entry_id.", ephemeral=True
                    )
                    return
                ok = await KnowledgeRepository.delete(session, entry_id)
                await interaction.response.send_message(
                    f"Removed entry #{entry_id}." if ok
                    else f"Entry #{entry_id} not found.",
                    ephemeral=not ok,
                )
                return

            if action == "search":
                if not query:
                    await interaction.response.send_message(
                        "`search` requires query.", ephemeral=True
                    )
                    return
                results = await KnowledgeRepository.search(session, query, limit=5)
                if not results:
                    await interaction.response.send_message(
                        "No knowledge entries matched.", ephemeral=True
                    )
                    return
                lines = [
                    f"**#{e.id}** [{e.category or 'uncategorized'}] "
                    f"(priority {e.priority}) — {e.question[:80]}"
                    for e in results
                ]
                await interaction.response.send_message(
                    "**Knowledge search results:**\n" + "\n".join(lines[:10])
                )
                return

            if action == "list":
                entries = await KnowledgeRepository.list_all(session, limit=15)
                if not entries:
                    await interaction.response.send_message(
                        "No knowledge entries.", ephemeral=True
                    )
                    return
                lines = [
                    f"**#{e.id}** [{e.category or 'uncategorized'}] "
                    f"(priority {e.priority}) — {e.question[:80]}"
                    for e in entries
                ]
                await interaction.response.send_message(
                    "**Knowledge entries:**\n" + "\n".join(lines)
                )
                return

            await interaction.response.send_message(
                "Unknown action. Use add, remove, search or list.", ephemeral=True
            )
