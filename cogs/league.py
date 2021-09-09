import discord
from discord.ext import commands
from riotwatcher import LolWatcher, ApiError
import secrets
import asyncio

secret = 'RGAPI-5153c113-d647-4546-a02d-81d69653054c'

class League(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.watcher = LolWatcher(secrets.riotKey, default_match_v5=True)
        
    @commands.command(name='isInt')
    async def isInting(self, pCtx, SummName):
        player = self.watcher.summoner.by_name('EUW1',SummName)
        activeGame = self.watcher.spectator.by_summoner('EUW1',player['id'])
        for p in activeGame['participants']:
            if p['summonerName'] == SummName:
                summoner = p
        kills = summoner['kills']
        deaths = summoner['deaths']
        if kills >= deaths:
            await pCtx.send("NO INT")
        else:
            await pCtx.send("HE'S FUKIN UHHH-- COPPER")  

def setup(bot):
    bot.add_cog(League(bot))