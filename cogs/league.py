import discord
from discord.ext import commands
from riotwatcher import LolWatcher, ApiError
import secrets
import asyncio

class League(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.watcher = LolWatcher(secrets.riotKey)
        
    @commands.command(name='last5')
    async def last5(self, pCtx, *SummName):
        SummonerName = ' '.join(SummName)
        player = self.watcher.summoner.by_name('EUW1',SummonerName)
        puuid = player['puuid']
        matchlist = self.watcher.match.matchlist_by_puuid('EUROPE',puuid)
        embed = discord.Embed(title=f"{SummonerName}'s Last 5 Games", color=0x4287f5)
        for i in range(0,5):
            try:
                match = self.watcher.match.by_id('EUROPE',matchlist[i])
            except Exception as e:
                print(e)
            for j in range(0,len(match['metadata']['participants'])):
                if match['metadata']['participants'][j] == puuid:
                    participant = j
                    break
            match_info = match['info']
            player_info = match_info['participants'][participant]
            kills = player_info['kills']
            assists = player_info['assists']
            deaths = player_info['deaths']
            if deaths == 0:
                deaths = 1; 
            kda = (kills+assists)/deaths
            if match_info['gameMode'] == 'CLASSIC':
                gameMode = "SR"
            elif match_info['gameMode'] == 'URF':
                gameMode = "URF"
            elif match_info['gameMode'] == 'ONEFORALL':
                gameMode = "OFA"
            elif match_info['gameMode'] == 'NEXUSBLITZ':
                gameMode = "NEXUS"
            elif match_info['gameMode'] == 'ULTBOOK':
                gameMode = "ULTBOOK"
            elif match_info['gameMode'] == 'ARAM':
                gameMode = "ARAM"
            elif match_info['gameMode'] == 'ARURF':
                gameMode = "ARURF"
            if player_info['win']:
                win = "W"
            elif player_info['gameEndedInEarlySurrender']:
                win = "R"
            else:
                win = "L"
            embed.add_field(name=f"{player_info['championName']} - {gameMode}", value=f"KDA: {round(kda,2)}\nOutcome: {win}", inline=False)


        await pCtx.send(embed=embed)

def setup(bot):
    bot.add_cog(League(bot))