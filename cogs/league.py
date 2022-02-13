import discord
import json
import math
from discord.ext import commands
from riotwatcher import LolWatcher, ApiError
import secrets
import asyncio

class League(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.watcher = LolWatcher(secrets.riotKey)
        versions = self.watcher.data_dragon.versions_for_region('euw')
        champions_version = versions['n']['champion']
        self.champList = self.watcher.data_dragon.champions(champions_version)
        icon_version = versions['n']['profileicon']
        self.baseRankURL = "https://thebestcomputerscientist.co.uk/leagueranks/Emblem_"
        self.iconList = self.watcher.data_dragon.profile_icons(icon_version)
        self.summonerList = self.watcher.data_dragon.summoner_spells(versions['n']['summoner'])
        self.runesList = self.watcher.data_dragon.runes_reforged(icon_version)
        self.iconURL = f"https://ddragon.leagueoflegends.com/cdn/{icon_version}/img/profileicon/"
        self.champURL = f"https://ddragon.leagueoflegends.com/cdn/{icon_version}/img/champion/"
        
    @commands.command(aliases=['league_rank', 'leaguerank'])
    async def _getrank(self ,pCtx, *SummName):
        SummonerName = ' '.join(SummName)
        try:
            player = self.watcher.summoner.by_name('EUW1',SummonerName)
        except Exception as e:
            print(e)
        id = player['id']
        try:
            data = self.watcher.league.by_summoner('EUW1', id)
        except Exception as e:
            print(e)
        for entry in data:
            if entry['queueType'] == 'RANKED_SOLO_5x5':
                soloData = entry
        if soloData is None:
            await pCtx.send("Error finding ranked solo/duo stats.")
            return
        embed = discord.Embed(title=f"{SummonerName} Ranked Solo/Duo Stats", color=0x19126e)
        embed.add_field(name="Dubs", value=f"{str(soloData['wins'])}", inline=True)
        embed.add_field(name="Losed", value=f"{str(soloData['losses'])}", inline=True)
        embed.add_field(name="Elo Pts", value=f"{str(soloData['leaguePoints'])}", inline=True)
        thumbnail_url = self.baseRankURL + str(soloData['tier']).capitalize() + '.png'
        embed.set_thumbnail(url=thumbnail_url)
        embed.set_footer(text=f"{str(soloData['tier']).capitalize()} {str(soloData['rank'])}")
        await pCtx.send(embed=embed)

    @commands.command(aliases=['league_current','leaguecurrent'])
    async def _currentgame(self, pCtx, *SummName):
        SummonerName = ' '.join(SummName)
        try:
            player = self.watcher.summoner.by_name('EUW1',SummonerName)
        except Exception as e:
            print(e)
        id = player['id']
        try:
            current_game_info = self.watcher.spectator.by_summoner('EUW1', id)
        except Exception as e:
            await pCtx.send(f"{SummonerName} is not in a match right now.")
    
        for i in current_game_info['participants']:
            if i['summonerName'] == SummonerName:
                player = i
                break
        try:
            for value in self.champList['data'].values():
                if int(value['key']) == player['championId']:
                    champ = value
                    break
        except Exception as e:
            print(e)
        embed = discord.Embed(title=f"{champ['id']}", color=0x362eb0)
        for value in self.iconList['data'].values():
            if int(value['id']) == player['profileIconId']:
                icon = value
                break
        try:
            embed.set_author(name=f"{SummonerName}", url="", icon_url=self.iconURL + str(icon['id']) + '.png')
        except Exception as e:
            print(e)

        for value in self.summonerList['data'].values():
            if int(value['key']) == player['spell1Id']:
                spell1 = value
            if int(value['key']) == player['spell2Id']:
                spell2 = value
        gameSeconds = current_game_info['gameLength']
        gameMinutes = math.floor(gameSeconds/60)
        gameSeconds = gameSeconds % 60

        playerPrimary = player['perks']['perkIds'][0]
        perkSecondaryStyle = player['perks']['perkSubStyle']
        #Find primary rune
        found = False
        for tree in self.runesList:
            for slot in tree['slots']:
                for runes in slot['runes']:
                    if runes['id'] == playerPrimary:
                        primary = runes['key']
                        found = True
                        break
                if found:
                    break
            if found:
                break
        
        #Secondary tree
        if perkSecondaryStyle == 8100:
            secondTree = "Domination"
        elif perkSecondaryStyle == 8300:
            secondTree = "Inspiration"
        elif perkSecondaryStyle == 8000:
            secondTree = "Precision"
        elif perkSecondaryStyle == 8400:
            secondTree = "Resolve"
        elif perkSecondaryStyle == 8200:
            secondTree = "Sorcery"
            
        mode = current_game_info['gameMode']
        
        embed.set_thumbnail(url=self.champURL + champ['image']['full'])
        embed.add_field(name="Game Time",value=f"{gameMinutes}:{gameSeconds}", inline=True)
        embed.add_field(name="Mode", value=f"{mode}", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="Spell 1", value=f"{spell1['name']}", inline=True)
        embed.add_field(name="Spell 2", value=f"{spell2['name']}", inline=True)
        embed.add_field(name="\u200b\u200b", value="\u200b", inline=True)
        embed.add_field(name="1º Rune", value=f'{primary}', inline=True)
        embed.add_field(name="2º Rune Tree", value=f'{secondTree}', inline=True)
        await pCtx.send(embed=embed)
        
    @commands.command(aliases=['league_last5', 'leaguelast5'])
    async def _last5(self, pCtx, *SummName):
        SummonerName = ' '.join(SummName)
        try:
            player = self.watcher.summoner.by_name('EUW1',SummonerName)
        except Exception as e:
            print(e)
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