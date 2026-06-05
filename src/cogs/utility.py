"""
Utility cog — server info, user info, polls, reminders.
"""

from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from src.utils.database import add_reminder, get_due_reminders, mark_reminder_done
from src.utils.helpers import parse_duration


class Utility(commands.Cog):
    """Useful commands for server management."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.reminder_check.start()

    def cog_unload(self) -> None:
        self.reminder_check.cancel()

    # --- Server Info ---

    @app_commands.command(name="serverinfo", description="Display server information")
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        embed = discord.Embed(
            title=guild.name,
            color=discord.Color.blurple(),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="Members", value=str(guild.member_count), inline=True)
        embed.add_field(name="Channels", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Boosts", value=str(guild.premium_subscription_count), inline=True)
        embed.add_field(
            name="Created",
            value=f"<t:{int(guild.created_at.timestamp())}:R>",
            inline=True,
        )
        embed.set_footer(text=f"Server ID: {guild.id}")
        await interaction.response.send_message(embed=embed)

    # --- User Info ---

    @app_commands.command(name="userinfo", description="Display information about a user")
    @app_commands.describe(member="The member to inspect (default: yourself)")
    async def userinfo(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None,
    ) -> None:
        member = member or interaction.user
        assert isinstance(member, discord.Member)

        embed = discord.Embed(
            title=str(member),
            color=member.color if member.color != discord.Color.default() else discord.Color.blurple(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
        embed.add_field(name="Bot", value="Yes" if member.bot else "No", inline=True)
        embed.add_field(
            name="Account Created",
            value=f"<t:{int(member.created_at.timestamp())}:R>",
            inline=True,
        )
        embed.add_field(
            name="Joined Server",
            value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Top Role",
            value=member.top_role.mention if member.top_role.name != "@everyone" else "@everyone",
            inline=True,
        )
        await interaction.response.send_message(embed=embed)

    # --- Polls ---

    @app_commands.command(name="poll", description="Create a poll")
    @app_commands.describe(
        question="The poll question",
        options="Options separated by | (e.g. Option 1 | Option 2 | Option 3)",
    )
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        options: str,
    ) -> None:
        option_list = [o.strip() for o in options.split("|") if o.strip()]

        if len(option_list) < 2:
            await interaction.response.send_message(
                "Provide at least 2 options separated by `|`.", ephemeral=True
            )
            return
        if len(option_list) > 9:
            await interaction.response.send_message(
                "Maximum 9 options allowed (Discord reaction limit).", ephemeral=True
            )
            return

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]

        embed = discord.Embed(
            title=question,
            color=discord.Color.gold(),
        )
        description_lines = []
        for i, option in enumerate(option_list):
            description_lines.append(f"{emojis[i]}  {option}")
        embed.description = "\n\n".join(description_lines)
        embed.set_footer(text=f"Poll by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()

        for i in range(len(option_list)):
            await msg.add_reaction(emojis[i])

    # --- Reminders ---

    @app_commands.command(name="remind", description="Set a reminder")
    @app_commands.describe(
        duration="When to remind (e.g. 10m, 2h, 1d)",
        message="What to remind you about",
    )
    async def remind(
        self,
        interaction: discord.Interaction,
        duration: str,
        message: str,
    ) -> None:
        td = parse_duration(duration)
        if td is None:
            await interaction.response.send_message(
                "Invalid duration. Use: `10m`, `2h`, `1d`, `1w`.", ephemeral=True
            )
            return

        remind_at = datetime.utcnow() + td
        reminder_id = await add_reminder(
            guild_id=interaction.guild_id or 0,
            channel_id=interaction.channel_id,
            user_id=interaction.user.id,
            message=message,
            remind_at=remind_at.isoformat(),
        )

        embed = discord.Embed(
            title="Reminder Set",
            description=(
                f"I'll remind you in **{duration}**:\n{message}"
            ),
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Reminder ID: {reminder_id}")
        await interaction.response.send_message(embed=embed)

    # --- Background task: check reminders ---

    @tasks.loop(seconds=30)
    async def reminder_check(self) -> None:
        """Poll the DB for due reminders and send them."""
        due = await get_due_reminders()
        for r in due:
            channel = self.bot.get_channel(r["channel_id"])
            if not channel:
                await mark_reminder_done(r["id"])
                continue

            assert isinstance(channel, discord.abc.Messageable)
            try:
                await channel.send(
                    f"⏰ <@{r['user_id']}> — **Reminder:** {r['message']}"
                )
            except discord.HTTPException:
                pass

            await mark_reminder_done(r["id"])

    @reminder_check.before_loop
    async def before_reminder_check(self) -> None:
        await self.bot.wait_until_ready()

    # --- Ping ---

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction) -> None:
        latency_ms = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="Pong!",
            description=f"Latency: **{latency_ms}ms**",
            color=discord.Color.green() if latency_ms < 200 else discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)

    # --- Error handling ---

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"Slow down! Try again in {error.retry_after:.1f}s.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"An error occurred: {error}", ephemeral=True
            )
