import discord,secrets
from discord.ext import commands

class Music(commands.Cog):
    def __init__(self,bot:commands.Bot)->None:
        self.bot = bot

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot), guild=secrets.testGuild)
