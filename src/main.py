"""
Discord Bot — Entry Point

Usage:
    python -m src.main
"""

import asyncio
import sys
from pathlib import Path

import discord
from discord.ext import commands

from src.config import DISCORD_TOKEN, BOT_PREFIX
from src.utils.database import get_db


class Bot(commands.Bot):
    """Custom Bot class with setup_hook for async initialization."""

    async def setup_hook(self) -> None:
        # Initialize database on startup
        db = await get_db()
        await db.close()

        # Load cogs
        await self.load_extension("src.cogs.ai_chat")
        await self.load_extension("src.cogs.moderation")
        await self.load_extension("src.cogs.utility")

        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash commands.")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    async def on_ready(self) -> None:
        assert self.user is not None
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Guilds: {len(self.guilds)}")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"{BOT_PREFIX}help | /ask",
            )
        )


async def main() -> None:
    if not DISCORD_TOKEN:
        print("ERROR: DISCORD_TOKEN not set. Copy .env.example to .env and fill in your token.")
        sys.exit(1)

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = Bot(
        command_prefix=BOT_PREFIX,
        intents=intents,
        help_command=commands.DefaultHelpCommand(no_category="General"),
    )

    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
