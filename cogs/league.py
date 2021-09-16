import discord
from discord.ext import commands
from riotwatcher import LolWatcher, ApiError
import secrets
import asyncio

class League(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.watcher = LolWatcher(secrets.riotKey, default_match_v5=True)
        
    @commands.command(name='isInt')
    async def isInting(self, pCtx, SummName):
        player = self.watcher.summoner.by_name('EUW1',SummName)
        puuid = player['puuid']
        matchlist = self.watcher.match.matchlist_by_puuid('EUROPE',puuid)
        averageKD = 0
        for i in range(0,5):
            match = self.watcher.match_v5.by_id('EUROPE',matchlist[i])
            for j in range(0,len(match['metadata']['participants'])):
                if match['metadata']['participants'][j] == puuid:
                    participant = j
                    break
            kills = match['info']['participants'][j]['kills']
            deaths = match['info']['participants'][j]['deaths']
            averageKD += kills/deaths
        averageKD /= 5
        if averageKD < 1.0:
            await pCtx.send("HE'S FUKIN UHHH-- COPPER\n{:.2f}".format(averageKD))
        else:
            await pCtx.send("THERE BE NO INT")
        #if kills >= deaths:
        #    await pCtx.send("NO INT")
        #else:
        #    await pCtx.send("HE'S FUKIN UHHH-- COPPER")  

def setup(bot):
    bot.add_cog(League(bot))