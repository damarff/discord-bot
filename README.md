# AI Discord Bot

A professional AI-powered Discord bot with moderation, AI chat, and utility features. Built with discord.py 2.x and DashScope Qwen.

## Features

- **AI Chat** — Mention the bot or use `/ask` to chat with AI (DashScope Qwen, OpenAI-compatible API)
- **Auto-Moderation** — Profanity filter + spam detection with auto-mute
- **Moderation Commands** — Kick, ban, mute, unmute, mod logs
- **Utility** — Server info, user info, polls, reminders, ping

## Quick Start

```bash
# 1. Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your Discord token + DashScope API key

# 3. Run
python -m src.main
```

## Configuration (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Bot token from Discord Developer Portal | *(required)* |
| `DASHSCOPE_API_KEY` | DashScope API key | *(required for AI)* |
| `DASHSCOPE_BASE_URL` | API base URL | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `DASHSCOPE_MODEL` | Model name | `qwen-plus` |
| `BOT_PREFIX` | Command prefix | `!` |
| `MAX_CONTEXT_MESSAGES` | AI context window size | `10` |

## Project Structure

```
src/
├── main.py            # Bot entry point
├── config.py          # Loads config from .env
├── cogs/
│   ├── ai_chat.py     # AI chat (mention, /ask, !ask)
│   ├── moderation.py  # Auto-mod + mod commands
│   └── utility.py     # Server/user info, polls, reminders
└── utils/
    ├── database.py    # SQLite (mod logs, reminders, AI context)
    └── helpers.py     # Duration parsing, formatting
```

## Requirements

- Python 3.11+
- discord.py 2.x
- aiohttp
- aiosqlite
- APScheduler
- python-dotenv

See `requirements.txt` for exact versions.

## Discord Bot Permissions

When inviting the bot, grant these permissions:
- Kick Members
- Ban Members
- Moderate Members (timeout)
- Manage Messages
- Send Messages
- Read Message History
- Add Reactions

## License

MIT
