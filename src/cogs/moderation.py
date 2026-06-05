"""
Moderation cog — auto-mod, kick/ban, mute/unmute.
"""

import re
from collections import defaultdict
from time import time

import discord
from discord import app_commands
from discord.ext import commands

from src.config import (
    BANNED_WORDS,
    SPAM_THRESHOLD,
    SPAM_WINDOW_SECONDS,
)
from src.utils.database import log_mod_action, get_mod_logs
from src.utils.helpers import parse_duration, format_timedelta


class Moderation(commands.Cog):
    """Server moderation tools."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # spam tracker: {channel_id: {user_id: [timestamps]}}
        self._spam_tracker: dict[int, dict[int, list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )

    # --- Auto-moderation ---

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        await self._check_profanity(message)
        await self._check_spam(message)

    async def _check_profanity(self, message: discord.Message) -> None:
        """Delete messages containing banned words and warn the user."""
        if not message.content:
            return

        lower = message.content.lower()
        for word in BANNED_WORDS:
            if re.search(rf"\b{re.escape(word)}\b", lower):
                try:
                    await message.delete()
                except discord.HTTPException:
                    return  # already deleted or no perms

                embed = discord.Embed(
                    title="Message Removed",
                    description=f"{message.author.mention}, your message was removed for inappropriate language.",
                    color=discord.Color.orange(),
                )
                try:
                    await message.channel.send(embed=embed, delete_after=10)
                except discord.HTTPException:
                    pass

                await log_mod_action(
                    guild_id=message.guild.id,
                    user_id=message.author.id,
                    moderator_id=self.bot.user.id if self.bot.user else 0,
                    action="auto-mod",
                    reason=f"Profanity filter triggered: '{word}'",
                )
                return  # one strike per message

    async def _check_spam(self, message: discord.Message) -> None:
        """Detect spam: N messages within a short time window."""
        if not message.guild or not self.bot.user:
            return

        now = time()
        tracker = self._spam_tracker[message.guild.id][message.author.id]

        # Add current timestamp and prune old ones
        tracker.append(now)
        cutoff = now - SPAM_WINDOW_SECONDS
        self._spam_tracker[message.guild.id][message.author.id] = [
            t for t in tracker if t > cutoff
        ]

        if len(self._spam_tracker[message.guild.id][message.author.id]) > SPAM_THRESHOLD:
            try:
                timeout_duration = discord.utils.utcnow() + __import__("datetime").timedelta(minutes=5)
                await message.author.timeout(timeout_duration, reason="Auto-moderation: spam detected")
            except (discord.HTTPException, AttributeError):
                pass

            try:
                await message.channel.send(
                    f"{message.author.mention} — muted for 5 minutes (spam detected).",
                    delete_after=15,
                )
            except discord.HTTPException:
                pass

            await log_mod_action(
                guild_id=message.guild.id,
                user_id=message.author.id,
                moderator_id=self.bot.user.id,
                action="auto-mute",
                reason="Spam detection threshold exceeded",
            )
            # Reset tracker
            self._spam_tracker[message.guild.id][message.author.id] = []

    # --- Kick ---

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="Member to kick", reason="Reason for kick")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ) -> None:
        if member.top_role >= interaction.user.top_role:  # type: ignore[union-attr]
            await interaction.response.send_message(
                "You can't kick someone with an equal or higher role.", ephemeral=True
            )
            return

        if member.top_role >= interaction.guild.me.top_role:  # type: ignore[union-attr]
            await interaction.response.send_message(
                "I can't kick this member — their role is too high.", ephemeral=True
            )
            return

        await member.kick(reason=reason)
        await log_mod_action(
            guild_id=interaction.guild_id or 0,
            user_id=member.id,
            moderator_id=interaction.user.id,
            action="kick",
            reason=reason,
        )
        embed = discord.Embed(
            title="Member Kicked",
            description=f"**{member}** has been kicked.\n**Reason:** {reason}",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)

    # --- Ban ---

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(member="Member to ban", reason="Reason for ban")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ) -> None:
        if member.top_role >= interaction.user.top_role:  # type: ignore[union-attr]
            await interaction.response.send_message(
                "You can't ban someone with an equal or higher role.", ephemeral=True
            )
            return

        if member.top_role >= interaction.guild.me.top_role:  # type: ignore[union-attr]
            await interaction.response.send_message(
                "I can't ban this member — their role is too high.", ephemeral=True
            )
            return

        await member.ban(reason=reason)
        await log_mod_action(
            guild_id=interaction.guild_id or 0,
            user_id=member.id,
            moderator_id=interaction.user.id,
            action="ban",
            reason=reason,
        )
        embed = discord.Embed(
            title="Member Banned",
            description=f"**{member}** has been banned.\n**Reason:** {reason}",
            color=discord.Color.dark_red(),
        )
        await interaction.response.send_message(embed=embed)

    # --- Mute (timeout) ---

    @app_commands.command(name="mute", description="Mute a member (timeout)")
    @app_commands.describe(
        member="Member to mute",
        duration="Duration (e.g. 10m, 2h, 1d)",
        reason="Reason for mute",
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str = "10m",
        reason: str = "No reason provided",
    ) -> None:
        td = parse_duration(duration)
        if td is None:
            await interaction.response.send_message(
                "Invalid duration format. Use: `10m`, `2h`, `1d`, `1w`.", ephemeral=True
            )
            return

        # Discord timeout max is 28 days
        from datetime import timedelta
        max_duration = timedelta(days=28)
        if td > max_duration:
            await interaction.response.send_message(
                "Maximum mute duration is 28 days.", ephemeral=True
            )
            return

        await member.timeout(
            discord.utils.utcnow() + td,
            reason=reason,
        )
        await log_mod_action(
            guild_id=interaction.guild_id or 0,
            user_id=member.id,
            moderator_id=interaction.user.id,
            action="mute",
            reason=f"{reason} (duration: {duration})",
        )
        embed = discord.Embed(
            title="Member Muted",
            description=(
                f"**{member}** has been muted for **{duration}**.\n"
                f"**Reason:** {reason}"
            ),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed)

    # --- Unmute ---

    @app_commands.command(name="unmute", description="Unmute a member")
    @app_commands.describe(member="Member to unmute")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        if not member.is_timed_out():
            await interaction.response.send_message(
                f"**{member}** is not currently muted.", ephemeral=True
            )
            return

        await member.timeout(None, reason="Unmuted by moderator")
        await log_mod_action(
            guild_id=interaction.guild_id or 0,
            user_id=member.id,
            moderator_id=interaction.user.id,
            action="unmute",
            reason="Manual unmute",
        )
        embed = discord.Embed(
            title="Member Unmuted",
            description=f"**{member}** has been unmuted.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    # --- Mod logs ---

    @app_commands.command(name="modlogs", description="View moderation logs for a member")
    @app_commands.describe(member="Member to check")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def modlogs(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        logs = await get_mod_logs(interaction.guild_id or 0, member.id)

        if not logs:
            await interaction.followup.send(f"No moderation logs found for **{member}**.")
            return

        embed = discord.Embed(
            title=f"Mod Logs — {member}",
            color=discord.Color.greyple(),
        )
        for entry in logs[:10]:  # show latest 10
            embed.add_field(
                name=f"{entry['action'].upper()} — {entry['created_at']}",
                value=f"Reason: {entry.get('reason') or 'N/A'}\nModerator: <@{entry['moderator_id']}>",
                inline=False,
            )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # --- Error handling ---

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You don't have permission to use this command.", ephemeral=True
            )
        elif isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(
                "I don't have the required permissions for this action.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"An error occurred: {error}", ephemeral=True
            )
