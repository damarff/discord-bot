# AI Discord Bot — Portfolio Project

> **Professional, AI-powered Discord bot** built with discord.py 2.x, featuring real-time AI chat, auto-moderation, and community tools.

---

## Features

### 🤖 AI Chat
- **Mention-triggered** — just mention the bot and ask anything
- **Slash command** — `/ask question: your question here`
- **Prefix command** — `!ask your question here`
- **Conversation context** — remembers recent messages per channel
- Powered by **DashScope Qwen** via OpenAI-compatible API

### 🛡️ Moderation
- **Auto-moderation** — profanity filter + spam detection
- **Slash commands** — `/kick`, `/ban`, `/mute`, `/unmute`
- **Mod logs** — all actions logged to SQLite, viewable with `/modlogs`
- **Timeout** — Discord-native timeout for muting

### 🧰 Utility
- **Server info** — `/serverinfo` — member count, roles, boosts, etc.
- **User info** — `/userinfo` — account age, roles, avatar
- **Polls** — `/poll` — create reaction-based polls instantly
- **Reminders** — `/remind` — set timed reminders with natural duration (10m, 2h, 1d)
- **Ping** — `/ping` — check bot latency

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.11+ | Runtime |
| discord.py 2.x | Discord API wrapper |
| aiohttp | Async HTTP for AI API calls |
| aiosqlite | Async SQLite for persistent storage |
| APScheduler | Background task scheduling (reminders) |
| python-dotenv | Environment variable management |
| DashScope Qwen | AI language model |

---

## Project Structure

```
discord-bot/
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
├── src/
│   ├── main.py            # Bot entry point
│   ├── config.py          # Configuration (loads from .env)
│   ├── cogs/
│   │   ├── ai_chat.py     # AI chat cog (DashScope Qwen)
│   │   ├── moderation.py  # Moderation cog
│   │   └── utility.py     # Utility commands cog
│   └── utils/
│       ├── database.py    # SQLite async helper
│       └── helpers.py     # Shared utility functions
├── data/
│   └── bot.db             # Auto-created SQLite database
└── assets/
    └── banner.md          # This file
```

---

## Setup

### 1. Clone & Install

```bash
cd discord-bot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your tokens
```

### 3. Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application → Bot → Copy token
3. Under **Bot** → Enable **Message Content Intent** and **Server Members Intent**
4. Under **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Kick Members`, `Ban Members`, `Moderate Members`, `Manage Messages`, `Send Messages`, `Read Message History`, `Add Reactions`
5. Use the generated URL to invite the bot

### 4. DashScope API

1. Get an API key from [Alibaba Cloud DashScope](https://dashscope.console.aliyun.com/)
2. Add it to your `.env` file

### 5. Run

```bash
python -m src.main
```

---

## Commands Reference

### AI
| Command | Description |
|---------|-------------|
| `@Bot question` | Mention the bot to get AI response |
| `/ask question:` | Slash command for AI chat |
| `!ask question:` | Prefix command for AI chat |
| `/clear_history` | Clear AI conversation history |

### Moderation
| Command | Description | Permission |
|---------|-------------|------------|
| `/kick member:` | Kick a member | Kick Members |
| `/ban member:` | Ban a member | Ban Members |
| `/mute member: duration:` | Mute (timeout) a member | Moderate Members |
| `/unmute member:` | Unmute a member | Moderate Members |
| `/modlogs member:` | View mod logs | Moderate Members |

### Utility
| Command | Description |
|---------|-------------|
| `/serverinfo` | Server information |
| `/userinfo member:` | User information |
| `/poll question: options:` | Create a poll |
| `/remind duration: message:` | Set a reminder |
| `/ping` | Check latency |

---

## Auto-Moderation

- **Profanity filter**: Automatically deletes messages containing banned words (configurable in `config.py`)
- **Spam detection**: Temporarily mutes users who send too many messages in a short window
- All auto-mod actions are logged to the database

---

## License

MIT — Free to use, modify, and distribute.

---

*Built as a portfolio project demonstrating Discord bot development with AI integration.*
