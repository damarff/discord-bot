"""
SQLite helper — async wrapper around aiosqlite.
Stores moderation logs, reminders, and AI conversation context.
"""

import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config import DB_PATH


async def get_db() -> aiosqlite.Connection:
    """Open (or create) the database and run migrations."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await _migrate(db)
    return db


async def _migrate(db: aiosqlite.Connection) -> None:
    """Create tables if they don't exist."""
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS mod_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id    INTEGER NOT NULL,
            user_id     INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            action      TEXT NOT NULL,  -- kick, ban, mute, warn
            reason      TEXT,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id    INTEGER NOT NULL,
            channel_id  INTEGER NOT NULL,
            user_id     INTEGER NOT NULL,
            message     TEXT NOT NULL,
            remind_at   TEXT NOT NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            triggered   INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS ai_context (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id  INTEGER NOT NULL,
            role        TEXT NOT NULL,  -- user or assistant
            content     TEXT NOT NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    await db.commit()


# --- Moderation Logs ---

async def log_mod_action(
    guild_id: int,
    user_id: int,
    moderator_id: int,
    action: str,
    reason: Optional[str] = None,
) -> None:
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO mod_logs (guild_id, user_id, moderator_id, action, reason) "
            "VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, moderator_id, action, reason),
        )
        await db.commit()
    finally:
        await db.close()


async def get_mod_logs(guild_id: int, user_id: int, limit: int = 10) -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM mod_logs WHERE guild_id = ? AND user_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (guild_id, user_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


# --- Reminders ---

async def add_reminder(
    guild_id: int,
    channel_id: int,
    user_id: int,
    message: str,
    remind_at: str,
) -> int:
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO reminders (guild_id, channel_id, user_id, message, remind_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (guild_id, channel_id, user_id, message, remind_at),
        )
        await db.commit()
        return cursor.lastrowid or 0
    finally:
        await db.close()


async def get_due_reminders() -> list[dict]:
    db = await get_db()
    try:
        now = datetime.utcnow().isoformat()
        cursor = await db.execute(
            "SELECT * FROM reminders WHERE triggered = 0 AND remind_at <= ?",
            (now,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def mark_reminder_done(reminder_id: int) -> None:
    db = await get_db()
    try:
        await db.execute(
            "UPDATE reminders SET triggered = 1 WHERE id = ?",
            (reminder_id,),
        )
        await db.commit()
    finally:
        await db.close()


# --- AI Context ---

async def add_ai_message(channel_id: int, role: str, content: str) -> None:
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO ai_context (channel_id, role, content) VALUES (?, ?, ?)",
            (channel_id, role, content),
        )
        await db.commit()
    finally:
        await db.close()


async def get_ai_context(channel_id: int, limit: int = 10) -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT role, content FROM ai_context "
            "WHERE channel_id = ? ORDER BY created_at DESC LIMIT ?",
            (channel_id, limit),
        )
        rows = await cursor.fetchall()
        # Reverse to get chronological order
        return list(reversed([dict(row) for row in rows]))
    finally:
        await db.close()


async def clear_ai_context(channel_id: int) -> None:
    db = await get_db()
    try:
        await db.execute(
            "DELETE FROM ai_context WHERE channel_id = ?",
            (channel_id,),
        )
        await db.commit()
    finally:
        await db.close()
