from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Integer,
    Enum,
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(BigInteger, primary_key=True)
    channel_id = Column(BigInteger, unique=True, nullable=False, index=True)
    guild_id = Column(BigInteger, nullable=False)
    creator_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    is_open = Column(Boolean, default=True)


class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticket_id = Column(
        BigInteger, ForeignKey("tickets.id"), nullable=False, index=True
    )
    discord_message_id = Column(BigInteger, unique=True, nullable=False)
    author_id = Column(BigInteger, nullable=False)
    author_type = Column(
        Enum("user", "bot", name="author_type_enum"), default="user", nullable=False
    )
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    ticket = relationship("Ticket", backref="messages")


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    keywords = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    source = Column(
        Enum("manual", "discord", name="source_enum"), default="manual", nullable=False
    )
    priority = Column(Integer, default=0, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class KnowledgeChannelMessage(Base):
    __tablename__ = "knowledge_channel_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(BigInteger, nullable=False, index=True)
    message_id = Column(BigInteger, unique=True, nullable=False)
    author_id = Column(BigInteger, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    indexed_at = Column(DateTime, default=datetime.utcnow)


class Escalation(Base):
    __tablename__ = "escalations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(
        BigInteger, ForeignKey("tickets.id"), nullable=False, index=True
    )
    triggered_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False, nullable=False)
    reason = Column(Text, nullable=True)
    last_notified = Column(DateTime, nullable=True)


class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(
        BigInteger, ForeignKey("tickets.id"), nullable=False, index=True
    )
    user_message_id = Column(BigInteger, nullable=False)
    request_timestamp = Column(DateTime, default=datetime.utcnow)
    response = Column(Text, nullable=True)
    model = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    error = Column(Text, nullable=True)
