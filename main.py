import asyncio
import os
import re

import discord
import requests
from discord import app_commands
from discord.ext import commands

# Credit for regex + yoinker to @ravy (https://ravy.pink) from https://aero.bot
EMOJI_REGEX = r"^<(?P<animated>a)?:(?P<name>[\w-]+):(?P<id>\d{17,19})>$"


def get_emoji_url(id_, animated):
    return f"https://cdn.discordapp.com/emojis/{id_}.{'gif' if animated else 'png'}?size=256&quality=lossless"


# no prefixes for message commands
BOT = commands.Bot(command_prefix=(), intents=discord.Intents.default())


async def emoji_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    names = list(set(emoji.name for emoji in interaction.guild.emojis))
    return [
        app_commands.Choice(
            name=f"{name} ({len([x for x in interaction.guild.emojis if x.name == name])})",
            value=name
        )
        for name
        in names
        if current in name
    ]


class EmojiCog(commands.GroupCog, name="emoji"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="add", description="register a new emoji")
    async def add_emoji(self, interaction: discord.Interaction, emoji: str, count: int = 1, name: str | None = None):
        await interaction.response.defer(thinking=True)
        response = await interaction.original_response()
        if (match := re.match(EMOJI_REGEX, emoji)) is None:
            return await response.edit(content=f"got `{emoji}` which didn't match `{EMOJI_REGEX}`")
        display_name = (name or match.group("name"))
        emoji_url = get_emoji_url(match.group("id"), match.group("animated"))
        emoji_bytes = requests.get(emoji_url).content
        new_emoji = None
        for _ in range(count):
            new_emoji = await interaction.guild.create_custom_emoji(
                name=display_name,
                image=emoji_bytes,
                reason=f"yoinked by {interaction.user}"
            )
        await response.edit(content=f"yoinked {display_name} {new_emoji}")
        await interaction.guild.fetch_emojis()

    @app_commands.command(name="remove", description="unregister an emoji")
    @app_commands.autocomplete(name=emoji_autocomplete)
    async def remove_emoji(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(thinking=True)
        response = await interaction.original_response()
        await interaction.guild.fetch_emojis()
        for emoji in interaction.guild.emojis:
            if emoji.name == name:
                await interaction.guild.delete_emoji(emoji, reason=f"deleted by {interaction.user}")
        await response.edit(content=f"removed {name}")
        await interaction.guild.fetch_emojis()


async def setup(bot: commands.Bot):
    await bot.add_cog(EmojiCog(bot))


@BOT.event
async def on_ready():
    print(f"conneccted as {BOT.user}")
    for guild_id in os.environ.get("GUILD_IDS", "").split(","):
        try:
            guild = discord.Object(id=int(guild_id.strip()))
        except ValueError:
            print(f"this doesn't look like a guild id: '{guild_id}'")
            continue
        BOT.tree.copy_global_to(guild=guild)
        await BOT.tree.sync(guild=guild)


if __name__ == "__main__":
    asyncio.run(setup(BOT))
    BOT.run(os.environ["DISCORD_TOKEN"])
