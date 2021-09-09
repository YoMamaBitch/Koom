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

    @commands.command(name='MRMStats')
    async def MostRecentStats(self, pCtx, Name):
        player = self.lolwatcher.summoner.by_name('EUW1',Name)
        match = self.watcher.match.matchlist_by_puuid('EUW1',player['puuid'])[0]
        test = 0


def setup(bot):
    bot.add_cog(Valorant(bot))
