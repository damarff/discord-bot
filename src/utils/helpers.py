"""
Shared utility functions.
"""

import re
from datetime import datetime, timedelta
from typing import Optional


def parse_duration(duration_str: str) -> Optional[timedelta]:
    """
    Parse a human-readable duration string into a timedelta.
    Supported formats: 10m, 2h, 1d, 1w  (m=minutes, h=hours, d=days, w=weeks)
    """
    match = re.match(r"^(\d+)([mhdw])$", duration_str.strip().lower())
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    units = {
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
        "w": timedelta(weeks=amount),
    }
    return units.get(unit)


def format_timedelta(td: timedelta) -> str:
    """Human-readable string for a timedelta."""
    total_seconds = int(td.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


def truncate(text: str, max_length: int = 1024) -> str:
    """Truncate text to Discord embed field limit."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def timestamp_now() -> str:
    """ISO timestamp for DB storage."""
    return datetime.utcnow().isoformat()
