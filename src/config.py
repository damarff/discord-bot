"""
Bot configuration — loads from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# --- Discord ---
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
BOT_PREFIX: str = os.getenv("BOT_PREFIX", "!")
AI_CHANNEL_ID: int = int(os.getenv("AI_CHANNEL_ID", "0"))
MAX_CONTEXT_MESSAGES: int = int(os.getenv("MAX_CONTEXT_MESSAGES", "10"))

# --- DashScope / OpenAI-compatible API ---
DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL: str = os.getenv(
    "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
DASHSCOPE_MODEL: str = os.getenv("DASHSCOPE_MODEL", "qwen-plus")

# --- Database ---
DB_PATH: Path = Path(__file__).resolve().parent.parent / "data" / "bot.db"

# --- Moderation ---
SPAM_THRESHOLD: int = 5          # messages in window to trigger spam
SPAM_WINDOW_SECONDS: int = 10    # time window for spam detection
BANNED_WORDS: list[str] = [      # profanity filter (add more as needed)
    "damn", "hell", "shit", "fuck", "ass",
]

# --- AI ---
AI_SYSTEM_PROMPT: str = (
    "You are a helpful, friendly Discord bot assistant. "
    "Keep responses concise and relevant. Use markdown formatting where appropriate."
)
