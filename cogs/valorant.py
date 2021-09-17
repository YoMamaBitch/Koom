import discord
from discord.ext import commands
import asyncio
import secrets
from riotwatcher import ValWatcher
from riotwatcher import LolWatcher

class Valorant(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.watcher = ValWatcher(secrets.riotKey)
        self.lolwatcher = LolWatcher(secrets.riotKey)



def setup(bot):
    bot.add_cog(Valorant(bot))
