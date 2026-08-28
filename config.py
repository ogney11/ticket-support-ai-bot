import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()


class Config:
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")

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

    KNOWLEDGE_CHANNEL_IDS = [
        int(x.strip())
        for x in os.getenv("KNOWLEDGE_CHANNEL_IDS", "").split(",")
        if x.strip()
    ]

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
