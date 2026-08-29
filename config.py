import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()


class Config:
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    # Ordered fallback models tried in turn if the primary is unavailable,
    # decommissioned, or the key lacks access. Comma-separated.
    GROQ_MODEL_FALLBACKS = [
        m.strip()
        for m in os.getenv(
            "GROQ_MODEL_FALLBACKS",
            "openai/gpt-oss-20b,openai/gpt-oss-120b,groq/compound-mini",
        ).split(",")
        if m.strip()
    ]

    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

    SUPPORT_ROLE_ID = int(os.getenv("SUPPORT_ROLE_ID", "0"))

    TICKET_CATEGORY_IDS = [
        int(x.strip())
        for x in os.getenv("TICKET_CATEGORY_IDS", "").split(",")
        if x.strip()
    ]
    TICKET_CHANNEL_IDS = [
        int(x.strip())
        for x in os.getenv("TICKET_CHANNEL_IDS", "").split(",")
        if x.strip()
    ]
    TICKET_NAME_PATTERN = os.getenv("TICKET_NAME_PATTERN")

    # Whitelist mode: if non-empty, ONLY these channels are indexed.
    KNOWLEDGE_CHANNEL_IDS = [
        int(x.strip())
        for x in os.getenv("KNOWLEDGE_CHANNEL_IDS", "").split(",")
        if x.strip()
    ]

    # Index-all mode: when KNOWLEDGE_CHANNEL_IDS is empty and this is true,
    # every server text channel is indexed EXCEPT those in KNOWLEDGE_BLACKLIST_IDS
    # and the ticket channels/categories (which are never treated as knowledge).
    KNOWLEDGE_INDEX_ALL = os.getenv("KNOWLEDGE_INDEX_ALL", "true").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    KNOWLEDGE_BLACKLIST_IDS = [
        int(x.strip())
        for x in os.getenv("KNOWLEDGE_BLACKLIST_IDS", "").split(",")
        if x.strip()
    ]

    # How many past ticket messages to feed the model.
    HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "15"))

    # AI moderation of knowledge indexing: run every candidate message through
    # the model to decide if it is useful, reusable knowledge before storing it.
    KNOWLEDGE_AI_FILTER = os.getenv("KNOWLEDGE_AI_FILTER", "true").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    # Staff handover: when a member with SUPPORT_ROLE_ID writes in the ticket,
    # the bot stops answering. It resumes when the bot is @mentioned, or after
    # this many minutes without a staff message.
    STAFF_TIMEOUT_MINUTES = int(os.getenv("STAFF_TIMEOUT_MINUTES", "30"))

    # Anti-spam: max user messages per window seconds, and max messages per
    # ticket per window. Raise these to make the bot's "slow down" warning
    # less aggressive.
    RATE_LIMIT_PER_USER = int(os.getenv("RATE_LIMIT_PER_USER", "10"))
    RATE_LIMIT_PER_TICKET = int(os.getenv("RATE_LIMIT_PER_TICKET", "25"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    # Knowledge backfill on startup: scan existing channel history to build the
    # knowledge base. Set false to only index new messages going forward.
    KNOWLEDGE_BACKFILL = os.getenv("KNOWLEDGE_BACKFILL", "true").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    # Comma-separated channels to backfill; empty = all eligible channels.
    KNOWLEDGE_BACKFILL_CHANNELS = [
        int(x.strip())
        for x in os.getenv("KNOWLEDGE_BACKFILL_CHANNELS", "").split(",")
        if x.strip()
    ]
    # Max messages to scan per channel during backfill.
    KNOWLEDGE_BACKFILL_LIMIT = int(os.getenv("KNOWLEDGE_BACKFILL_LIMIT", "200"))

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        errors = []
        if not cls.DISCORD_TOKEN:
            errors.append("DISCORD_TOKEN not set")
        if not cls.GROQ_API_KEY:
            errors.append("GROQ_API_KEY not set")
        if not cls.MYSQL_USER or not cls.MYSQL_PASSWORD or not cls.MYSQL_DATABASE:
            errors.append("MySQL credentials not fully set")
        if cls.SUPPORT_ROLE_ID == 0:
            errors.append("SUPPORT_ROLE_ID not set")
        if errors:
            raise ValueError("; ".join(errors))
