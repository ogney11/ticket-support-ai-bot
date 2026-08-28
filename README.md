# Discord Ticket Support AI Bot

A production-ready Discord bot that serves as a professional AI support assistant, operating **exclusively inside support tickets**. Built with Python 3.12+, discord.py, the Groq API, and MySQL 8.4+.

## Features

- **Ticket-only operation** – the bot only responds in channels detected as tickets (by channel ID, category ID, or channel-name pattern).
- **AI answers** from your curated knowledge base, grounded via the Groq API.
- **Knowledge from two sources**: manually curated Q&A entries and automatically indexed messages from configured knowledge channels.
- **Smart escalation** – when the bot lacks knowledge or the AI is uncertain, it pings the support role (with a cooldown to prevent spam).
- **Full auditing** – every AI request is logged in `ai_usage_logs`.
- **Rate limiting** per user and per ticket.
- **Staff commands** to manage the knowledge base (`/knowledge add|remove|search|list`).

## Project structure

```
bot/
├── main.py                      # entry point
├── config.py                    # env loading + validation
├── database/                    # SQLAlchemy async models, connection, repositories
├── support/                     # ticket detector, message handler, knowledge listener, staff commands
├── ai/                          # Groq client, prompts, context builder
├── knowledge/                   # retrieval from DB + indexed discord messages
├── tickets/                     # per-ticket in-memory cache
├── escalation/                  # escalation manager with cooldown
├── utils/                       # logging, rate limiting
├── database/schema.sql          # MySQL DDL
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Requirements

- Python 3.12+
- MySQL 8.4+
- A Discord bot application with the **Message Content Intent** enabled
- A Groq API key

## Configuration

1. Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

Key settings:

| Variable | Description |
| --- | --- |
| `DISCORD_TOKEN` | Your bot token |
| `GROQ_API_KEY` | Your Groq API key |
| `GROQ_MODEL` | Groq model (default `openai/gpt-oss-20b`) |
| `GROQ_MODEL_FALLBACKS` | Comma-separated fallback models tried in turn if the primary is unavailable/decommissioned |
| `MYSQL_*` | MySQL connection details |
| `SUPPORT_ROLE_ID` | Role ID pinged when escalating |
| `TICKET_CATEGORY_IDS` | Comma-separated category IDs containing tickets |
| `TICKET_CHANNEL_IDS` | Comma-separated explicit ticket channel IDs |
| `TICKET_NAME_PATTERN` | Regex matched against channel names (e.g. `^ticket-`) |
| `KNOWLEDGE_CHANNEL_IDS` | Comma-separated channels to index as knowledge |
| `LOG_LEVEL` | `DEBUG`, `INFO`, etc. |

Ticket detection uses **any** of the three mechanisms (channel IDs, category IDs, or name pattern) that match. At least one is recommended.

## Setting up the Discord bot

1. Create an application at the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create a bot user and copy the token.
3. Under **Bot → Privileged Gateway Intents**, enable **Message Content Intent** (required to read message text).
4. Invite the bot with the following permissions: **View Channels**, **Read Message History**, **Send Messages**, **Mention @everyone** (and anything else your ticket system requires).
   - OAuth2 URL permissions scope: `bot`, `applications.commands`.

## Database

Create the schema before first run:

```bash
mysql -u root -p < database/schema.sql
```

The schema creates these tables:

- `tickets` – ticket channel info
- `ticket_messages` – all ticket messages (user + bot)
- `knowledge_entries` – curated Q&A knowledge base
- `knowledge_source` – metadata for knowledge entries
- `knowledge_channel_messages` – indexed messages from knowledge channels
- `bot_config` – runtime configuration cache
- `escalations` – unresolved escalations with cooldown data
- `ai_usage_logs` – audit log of every AI request

All tables use `utf8mb4`, proper foreign keys, indexes, and `BIGINT` for Discord IDs.

## Running locally

```bash
pip install -r requirements.txt
python -m bot.main
```

The bot validates required env vars on startup and raises a clear error if any are missing.

## Running with Docker

```bash
docker-compose up -d
```

The `db` service initializes from `database/schema.sql` on first start, and the `bot` service waits for the database health check before starting.

## Managing knowledge

Staff (members holding `SUPPORT_ROLE_ID`) can manage the knowledge base:

- `/knowledge add <question> <answer> [keywords] [category]`
- `/knowledge remove <entry_id>`
- `/knowledge search <query>`
- `/knowledge list`

Messages posted in any `KNOWLEDGE_CHANNEL_IDS` channel are automatically indexed into `knowledge_channel_messages` and become part of the retrieval pool.

## How the AI pipeline works

1. A message arrives in a ticket channel.
2. The message (and ticket, if new) is persisted.
3. Rate limits and greeting filters are applied.
4. Knowledge is retrieved from both the curated DB entries and the indexed Discord messages.
5. If nothing matches, the bot escalates to the support role.
6. Otherwise, a context (system prompt + knowledge + ticket history + user message) is sent to Groq as a JSON-object completion (`action` + `response`).
7. Responses are validated against a blocklist; unsafe or uncertain results trigger escalation.
8. The final answer is sent to the channel and stored; every request is audited.

## Security notes

- **Ticket isolation** – every message and AI context is scoped to the ticket ID.
- **Prompt injection** – user input is treated as data, never as system instructions; the system prompt forbids revealing internal instructions or knowledge sources.
- **No hardcoded secrets** – everything sensitive comes from the environment.
- **Escalation cooldown** – pings are rate-limited to avoid spam.

## Production considerations

- Use a real migration tool (e.g. Alembic) instead of the dev-time `create_all` in `on_ready`.
- For high throughput, move rate limiting/caching to Redis and scale workers horizontally.
- MySQL keyword `LIKE` search is sufficient for small knowledge bases; consider MySQL FULLTEXT or an external search engine for large ones.
