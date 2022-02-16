import discord
import json
import math
from discord.ext import commands
from riotwatcher import LolWatcher, ApiError
import secrets
import asyncio
from bson.objectid import ObjectId

class League(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.database = self.bot.db.league_friends
        self.activeQueries = []
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

    @commands.Cog.listener()
    async def on_message(self, message):
        for query in self.activeQueries:
            if query == message.author.id:
                #Check exists as a player
                SNR = await self._getSummonerNameAndRegion(message.content)
                try:
                    self.watcher.summoner.by_name(SNR[1],SNR[0])
                except Exception as e:
                    await message.channel.send("That summoner doesn't exist. Try again.")
                    return
                result = await self.database.insert_one({'_uid':query})
                await self.database.update_one({'_uid':query}, {'$set':{'_friends':[]}})
                self.activeQueries.remove(query)
                await message.channel.send("Successfully added :white_check_mark:")
                return

    @commands.command(aliases=['league_friends','leaguefriends','show_league_friends'])
    async def _list_league_friends(self, pCtx):
        try:
            thisUser = await self.database.find_one({'_uid':pCtx.message.author.id})
            if thisUser is None:
                raise Exception("ThisUser was None")
        except Exception as e:
            self.activeQueries.append(pCtx.message.author.id)
            await pCtx.send("You aren't in the League DB yet, fear not, type your summoner name with your #REGION at the end now, and you'll be added.")
            return

        try:
            result = await self.database.find_one({'_uid':pCtx.message.author.id})
        except Exception as e:
            self.activeQueries.append(pCtx.message.author.id)
            await pCtx.send("You aren't in the League DB yet, fear not, type your summoner name with your #REGION at the end now, and you'll be added.")
            return
        try:
            embed = discord.Embed(title=f"{pCtx.author.display_name}'s Friend List", color=0x19126e)
        except Exception as e:
            print(e)
        friends = result['_friends']
        field_str = '\u200b'
        for friend in friends:
            temp = friend.split('#')
            summoner = temp[0]
            region = temp[1]
            id = self.watcher.summoner.by_name(region, summoner)['id']
            try:
                game_info = self.watcher.spectator.by_summoner(region, id)
                gameSeconds = game_info['gameLength']
                gameMinutes = math.floor(gameSeconds/60)
                gameSeconds = gameSeconds % 60
                for i in game_info['participants']:
                    if i['summonerName'] == summoner:
                        player = i
                        break
                try:
                    for value in self.champList['data'].values():
                        if int(value['key']) == player['championId']:
                            champ = value
                            break
                except Exception as e:
                    print(e)
                friend_status = f"{gameMinutes:02d}:{gameSeconds:02d} - {champ['id']}"
            except Exception:
                friend_status = "Not in match"     
            
            field_str += f'**{summoner}** - {friend_status}\n'
        embed.add_field(name='\u200b', value=field_str, inline=False)
        await pCtx.send(embed=embed)

    @commands.command(aliases=['league_remove_friend','league_del_friend','leagueremovefriend','league_del','leaguedel','leagueremove','leaguedelfriend'])
    async def _remove_league_friend(self, pCtx, *SummName):
        try:
            thisUser = await self.database.find_one({'_uid':pCtx.message.author.id})
            if thisUser is None:
                raise Exception("ThisUser was None")
        except Exception as e:
            self.activeQueries.append(pCtx.message.author.id)
            await pCtx.send("You aren't in the League DB yet, fear not, type your summoner name with your #REGION at the end now, and you'll be added.")
            return
        SNR = await self._getSummonerNameAndRegion(*SummName)
        try:
            friend = self.watcher.summoner.by_name(SNR[1],SNR[0])
        except ApiError as e:
            if e.response.status_code == 404:
                await pCtx.send("No summoner with that name found.")
                return
            else:
                raise
        try:
            await self.database.update_one({'_uid':pCtx.message.author.id}, {'$pull':{'_friends':friend['name']+'#'+SNR[1]}})
        except Exception:
            await pCtx.send("Error removing friend.")
            return
        await pCtx.send(f"Successfully removed {friend['name']+'#'+SNR[1]} from your league friends list.")
        
    @commands.command(aliases=['league_add_friend', 'leagueadd', 'league_add', 'leagueaddfriend'])
    async def _add_league_friend(self, pCtx, *SummName):

        #Get current discord user from Database
        try:
            thisUser = await self.database.find_one({'_uid':pCtx.message.author.id})
            if thisUser is None:
                raise Exception("ThisUser was None")
        except Exception as e:
            self.activeQueries.append(pCtx.message.author.id)
            await pCtx.send("You aren't in the League DB yet, fear not, type your summoner name with your #REGION at the end now, and you'll be added.")
            return

        SNR = await self._getSummonerNameAndRegion(*SummName)
        SummonerName = SNR[0]
        Region = SNR[1]
        try:
            new_friend = self.watcher.summoner.by_name(Region,SummonerName)
        except ApiError as e:
            if e.response.status_code == 404:
                await pCtx.send("No summoner with that name found.")
                return
            else:
                raise
        for friend in thisUser['_friends']:
            if friend == new_friend['name']+SNR[1]:
                await pCtx.send("You've already added this player on your friends list.")
                return
        await self.database.update_one({'_uid':pCtx.message.author.id}, {'$push':{'_friends':new_friend['name']+'#'+SNR[1]}})
        await pCtx.send(f"Successfully added {new_friend['name'] + '#' + SNR[1]} to your friends list.")

    async def _getMatchRegionFromRegion(self, Region):
        if Region == 'EUW1' or Region == 'EUN1' or Region == 'RU' or Region == 'TR1':
            return "EUROPE"
        elif Region == 'LA1' or Region == 'LA2' or Region == 'NA1':
            return "AMERICAS"
        elif Region == 'OC1' or Region == 'JP1' or Region == 'KR':
            return "ASIA"
        return None
    
    async def _getSummonerNameAndRegion(self, *SummName):
        try:
            SummonerName = ' '.join(SummName)
            if SummonerName.find('#') == -1:
                Region = 'EUW1'
                return (SummonerName, 'EUW1')
            Region = SummonerName.split('#')[1]
        except Exception as e:
            print(e)

        if Region == 'EUW':
            Region = 'EUW1'
        elif Region == 'BR':
            Region = 'BR1'
        elif Region == 'EUN':
            Region = 'EUN1'
        elif Region == 'JP':
            Region = 'JP1'
        elif Region == 'NA':
            Region = 'NA1'
        elif Region == 'OC':
            Region = 'OC1'
        elif Region == 'TR':
            Region = 'TR1'

        SummonerName = SummonerName.split('#')[0]
        return (SummonerName,Region)

    @commands.command(aliases=['league_rank', 'leaguerank'])
    async def _getrank(self ,pCtx, *SummName):
        SummonerNameReg = await self._getSummonerNameAndRegion(*SummName)
        SummonerName = SummonerNameReg[0]
        Region = SummonerNameReg[1]
        try:
            player = self.watcher.summoner.by_name(Region,SummonerName)
            SummonerName = player['name']
        except Exception as e:
            print(e)
        id = player['id']
        try:
            data = self.watcher.league.by_summoner(Region, id)
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
        SummonerNameReg = await self._getSummonerNameAndRegion(*SummName)
        SummonerName = SummonerNameReg[0]
        Region = SummonerNameReg[1]
        try:
            player = self.watcher.summoner.by_name(Region,SummonerName)
        except Exception as e:
            print(e)
        id = player['id']
        try:
            current_game_info = self.watcher.spectator.by_summoner(Region, id)
        except Exception as e:
            await pCtx.send(f"{SummonerName} is not in a match right now.")
    
        for i in current_game_info['participants']:
            if i['summonerName'].lower() == SummonerName.lower():
                player = i
                SummonerName = i['summonerName']
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
        SummonerNameReg = await self._getSummonerNameAndRegion(*SummName)
        SummonerName = SummonerNameReg[0]
        Region = SummonerNameReg[1]    
        try:
            player = self.watcher.summoner.by_name(Region,SummonerName)
        except Exception as e:
            print(e)
        puuid = player['puuid']
        matchRegion = await self._getMatchRegionFromRegion(Region)
        if matchRegion is None:
            await pCtx.send("Error getting region data")
            return
        matchlist = self.watcher.match.matchlist_by_puuid(matchRegion,puuid)
        embed = discord.Embed(title=f"{SummonerName}'s Last 5 Games", color=0x4287f5)
        for i in range(0,5):
            try:
                match = self.watcher.match.by_id(matchRegion,matchlist[i])
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