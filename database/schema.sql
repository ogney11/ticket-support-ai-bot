-- Discord Ticket Support AI Bot - MySQL 8.4 schema
-- Run against the configured database (e.g. mysql db < schema.sql)

CREATE DATABASE IF NOT EXISTS ticket_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ticket_bot;

-- Tickets
CREATE TABLE IF NOT EXISTS tickets (
    id         BIGINT       NOT NULL,
    channel_id BIGINT       NOT NULL,
    guild_id   BIGINT       NOT NULL,
    creator_id BIGINT       NOT NULL,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at  DATETIME     NULL,
    is_open    BOOLEAN      NOT NULL DEFAULT TRUE,
    bot_paused BOOLEAN      NOT NULL DEFAULT FALSE,
    last_staff_message_at DATETIME NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_tickets_channel (channel_id),
    KEY idx_tickets_guild (guild_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Ticket messages
CREATE TABLE IF NOT EXISTS ticket_messages (
    id                  BIGINT   NOT NULL AUTO_INCREMENT,
    ticket_id           BIGINT   NOT NULL,
    discord_message_id  BIGINT   NOT NULL,
    author_id           BIGINT   NOT NULL,
    author_type         ENUM('user','bot') NOT NULL DEFAULT 'user',
    content             TEXT     NOT NULL,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_ticket_messages_discord (discord_message_id),
    KEY idx_ticket_messages_ticket (ticket_id),
    CONSTRAINT fk_ticket_messages_ticket
        FOREIGN KEY (ticket_id) REFERENCES tickets (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Knowledge entries
CREATE TABLE IF NOT EXISTS knowledge_entries (
    id         INT          NOT NULL AUTO_INCREMENT,
    question   TEXT         NOT NULL,
    answer     TEXT         NOT NULL,
    keywords   TEXT         NULL,
    category   VARCHAR(100) NULL,
    source     ENUM('manual','discord') NOT NULL DEFAULT 'manual',
    priority   INT          NOT NULL DEFAULT 0,
    active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                           ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_knowledge_entries_active (active),
    KEY idx_knowledge_entries_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Knowledge source metadata (per design docs)
CREATE TABLE IF NOT EXISTS knowledge_source (
    id            INT          NOT NULL AUTO_INCREMENT,
    entry_id      INT          NOT NULL,
    source_type   ENUM('manual','discord') NOT NULL DEFAULT 'manual',
    source_channel_id BIGINT   NULL,
    source_message_id BIGINT   NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_knowledge_source_entry (entry_id),
    CONSTRAINT fk_knowledge_source_entry
        FOREIGN KEY (entry_id) REFERENCES knowledge_entries (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Indexed messages from knowledge channels
CREATE TABLE IF NOT EXISTS knowledge_channel_messages (
    id         INT      NOT NULL AUTO_INCREMENT,
    channel_id BIGINT   NOT NULL,
    message_id BIGINT   NOT NULL,
    author_id  BIGINT   NOT NULL,
    content    TEXT     NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    indexed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_kcm_message (message_id),
    KEY idx_kcm_channel (channel_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Runtime config cache
CREATE TABLE IF NOT EXISTS bot_config (
    key        VARCHAR(100) NOT NULL,
    value      TEXT         NULL,
    updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                           ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Escalations
CREATE TABLE IF NOT EXISTS escalations (
    id            INT      NOT NULL AUTO_INCREMENT,
    ticket_id     BIGINT   NOT NULL,
    triggered_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved      BOOLEAN  NOT NULL DEFAULT FALSE,
    reason        TEXT     NULL,
    last_notified DATETIME NULL,
    PRIMARY KEY (id),
    KEY idx_escalations_ticket (ticket_id),
    CONSTRAINT fk_escalations_ticket
        FOREIGN KEY (ticket_id) REFERENCES tickets (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- AI usage logs
CREATE TABLE IF NOT EXISTS ai_usage_logs (
    id               INT          NOT NULL AUTO_INCREMENT,
    ticket_id        BIGINT       NOT NULL,
    user_message_id  BIGINT       NOT NULL,
    request_timestamp DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    response         TEXT         NULL,
    model            VARCHAR(100) NULL,
    tokens_used      INT          NULL,
    success          BOOLEAN      NOT NULL DEFAULT TRUE,
    error            TEXT         NULL,
    PRIMARY KEY (id),
    KEY idx_ai_usage_ticket (ticket_id),
    CONSTRAINT fk_ai_usage_ticket
        FOREIGN KEY (ticket_id) REFERENCES tickets (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
