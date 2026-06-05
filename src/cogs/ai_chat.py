"""
AI Chat cog — DashScope Qwen integration via OpenAI-compatible API.
"""

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from src.config import (
    DASHSCOPE_API_KEY,
    DASHSCOPE_BASE_URL,
    DASHSCOPE_MODEL,
    AI_SYSTEM_PROMPT,
    MAX_CONTEXT_MESSAGES,
)
from src.utils.database import add_ai_message, get_ai_context, clear_ai_context


class AiChat(commands.Cog):
    """AI-powered chat using DashScope Qwen API."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def cog_unload(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    # --- Core API call ---

    async def _chat_completion(self, messages: list[dict]) -> str:
        """Call DashScope OpenAI-compatible chat completion endpoint."""
        url = f"{DASHSCOPE_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": DASHSCOPE_MODEL,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7,
        }

        session = await self._get_session()
        try:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    return f"[API Error {resp.status}] {body[:200]}"
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
        except aiohttp.ClientError as e:
            return f"[Connection Error] {e}"
        except (KeyError, IndexError):
            return "[API Error] Unexpected response format."

    # --- Listener: mention trigger ---

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Respond when the bot is mentioned (outside of commands)."""
        if message.author.bot:
            return
        if not self.bot.user:
            return
        if self.bot.user not in message.mentions:
            return

        # Strip the mention from the message text
        clean = message.content
        for mention in message.mentions:
            clean = clean.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
        clean = clean.strip()

        if not clean:
            await message.reply("Ask me something! Example: `What's the capital of France?`")
            return

        await self._handle_ai_request(message.channel.id, clean, message)

    # --- Slash command: /ask ---

    @app_commands.command(name="ask", description="Ask the AI assistant a question")
    @app_commands.describe(question="Your question")
    async def ask_slash(self, interaction: discord.Interaction, question: str) -> None:
        await interaction.response.defer()
        response = await self._handle_ai_request(interaction.channel_id, question)

        # Follow up with the response (interaction is already deferred)
        if interaction.channel:
            await interaction.followup.send(
                embed=self._make_embed(question, response),
                allowed_mentions=discord.AllowedMentions.none(),
            )

    # --- Prefix command: !ask ---

    @commands.command(name="ask")
    async def ask_prefix(self, ctx: commands.Context, *, question: str) -> None:
        """Ask the AI a question using the bot prefix."""
        async with ctx.typing():
            response = await self._handle_ai_request(ctx.channel.id, question)
            await ctx.reply(
                embed=self._make_embed(question, response),
                allowed_mentions=discord.AllowedMentions.none(),
            )

    # --- Context management ---

    @app_commands.command(name="clear_history", description="Clear AI conversation history for this channel")
    async def clear_history(self, interaction: discord.Interaction) -> None:
        await clear_ai_context(interaction.channel_id)
        await interaction.response.send_message("Conversation history cleared.", ephemeral=True)

    # --- Internal helpers ---

    async def _handle_ai_request(
        self,
        channel_id: int,
        user_message: str,
        reply_to: discord.Message | None = None,
    ) -> str:
        """Build context, call API, store messages, return response."""
        # Save user message
        await add_ai_message(channel_id, "user", user_message)

        # Build messages array with system prompt + context
        context = await get_ai_context(channel_id, limit=MAX_CONTEXT_MESSAGES)
        messages = [{"role": "system", "content": AI_SYSTEM_PROMPT}]
        messages.extend(
            {"role": msg["role"], "content": msg["content"]} for msg in context
        )

        # Get response
        response = await self._chat_completion(messages)

        # Save assistant response
        await add_ai_message(channel_id, "assistant", response)

        # If triggered by mention, also reply to the original message
        if reply_to:
            try:
                await reply_to.reply(
                    embed=self._make_embed(user_message, response),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                pass  # Message too old or channel restrictions

        return response

    @staticmethod
    def _make_embed(question: str, answer: str) -> discord.Embed:
        embed = discord.Embed(
            title="AI Assistant",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Question", value=question[:1024], inline=False)
        embed.add_field(name="Answer", value=answer[:4096], inline=False)
        embed.set_footer(text="Powered by DashScope Qwen")
        return embed
