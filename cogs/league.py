from random import randrange
import discord,secrets, math, json, asyncio, sqlite3, utility, time
from league_view import LeagueMatchView
from typing import List
from utility import league_content_url
from riotwatcher import LolWatcher, ApiError
from discord.ext import commands
from discord.ui import Button, View
from discord import app_commands


class League(commands.Cog):
    def __init__(self,bot:commands.Bot)->None:
        self.bot = bot
        self.database = sqlite3.connect("database.sqlite")
        self.cursor : sqlite3.Cursor = self.database.cursor()
        self.watcher : LolWatcher = LolWatcher(secrets.leagueKey)
        versions = self.watcher.data_dragon.versions_for_region('euw')
        self.baseRankUrl = "https://thebestcomputerscientist.co.uk/leagueranks/Emblem_"
        self.champList = self.watcher.data_dragon.champions(versions['n']['champion'])
        self.iconList = self.watcher.data_dragon.profile_icons(versions['n']['profileicon'])
        self.summonerList = self.watcher.data_dragon.summoner_spells(versions['n']['summoner'])
        self.runesList = self.watcher.data_dragon.runes_reforged(versions['n']['profileicon'])
        self.iconUrl = f"https://ddragon.leagueoflegends.com/cdn/{versions['n']['profileicon']}/img/profileicon/"
        self.champUrl = f"https://ddragon.leagueoflegends.com/cdn/{versions['n']['profileicon']}/img/champion/"
        self.emoteUrl = f"https://raw.communitydragon.org/12.6/"
        self.activeMatchHistories = []
        self.positiveEmotes = []
        self.negativeEmotes = []
        with open ('leagueNegativeEmotes.txt', 'r', encoding='utf-8') as f:
            for line in f:
                self.negativeEmotes.append(line)
        with open('leaguePositiveEmotes.txt', 'r',encoding='utf-8') as f:
            for line in f:
                self.positiveEmotes.append(line)

    @app_commands.command(name='leaguematches',description="List your recent League games.")
    @app_commands.guilds(discord.Object(817238795966611466))
    async def leaguematches(self, interaction:discord.Interaction)->None:
        await interaction.response.defer()
        id = interaction.user.id
        author = interaction.user.display_name
        url = interaction.user.display_avatar.url
        if not self.checkIfUserLinked(id):
            embed= utility.generateLeagueFailedEmbed(text="Your discord account isn't linked to a league account, link with /linkleague", author=author, author_icon=url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        userdata = self.cursor.execute("SELECT * FROM League WHERE did is ?",(id,)).fetchone()
        league_name:str = userdata[1]
        league_puuid = userdata[2]
        league_id = userdata[3]
        regionNoNumber = league_name.split('#')[1].removesuffix('1').removesuffix('2')
        match_region = self.getMatchRegionFromUserRegion(regionNoNumber)
        player_matches_ids = self.watcher.match.matchlist_by_puuid(match_region, league_puuid, count=10)
        player_matches = []
        for i in player_matches_ids:
            player_matches.append(self.watcher.match.by_id(match_region, i))
        match_embed_data = [id,0,8]
        embed = self.generateMatchesEmbed(player_matches, league_puuid,league_id, author, url,match_embed_data)
        view = LeagueMatchView(match_embed_data, self)
        match_embed_data.append(view)
        self.activeMatchHistories.append(match_embed_data)
        await interaction.followup.send(embed=embed, view=view)
        #await interaction.response.send_message(embed=embed,view=view)

    @app_commands.command(name='leaguefriends',description="List your friends and their current games.")
    @app_commands.guilds(discord.Object(817238795966611466))
    async def leaguefriends(self, interaction:discord.Interaction)->None:
        id = interaction.user.id
        author = interaction.user.display_name
        url = interaction.user.display_avatar.url
        if not self.checkIfUserLinked(id):
            embed= utility.generateLeagueFailedEmbed(text="Your discord account isn't linked to a league account, link with /linkleague", author=author, author_icon=url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        friends_list = self.cursor.execute(f'SELECT friends FROM League WHERE did is {id}').fetchone()[0].split('`')
        embed = self.generateFriendsEmbed(id,friends_list,author,url)
        await interaction.response.send_message(embed=embed)

    @commands.command()
    async def delleague(self, ctx, friends_summoner):
        id = ctx.author.id
        author = ctx.author.display_name
        url = ctx.author.display_avatar.url
        if not self.checkIfUserLinked(id):
            embed= utility.generateLeagueFailedEmbed(text="Your discord account isn't linked to a league account, link with /linkleague", author=author, author_icon=url)
            await ctx.send(embed=embed)
            return
        friends = self.cursor.execute(f'SELECT friends From League WHERE did IS {id}').fetchone()
        friend_list = friends[0].split('`')
        friend_list.remove(friends_summoner)
        friends = '`'.join(friend_list)   
        self.cursor.execute('UPDATE League SET friends = ? WHERE did IS ?',(friends, id))
        self.database.commit()
        #embed = utility.generateLeagueSuccessEmbed(f"Successfully removed {friends_summoner} from your friend list.", author, url)
        await ctx.send(f"Successfully removed {friends_summoner} from your friend list.")

    @app_commands.command(name='delleague',description="Remove user from your league friends.")
    @app_commands.guilds(discord.Object(817238795966611466))
    async def delleagueApp(self, interaction:discord.Interaction, friend:discord.User)->None:
        id = interaction.user.id
        author = interaction.user.display_name
        url = interaction.user.display_avatar.url
        friend_id = friend.id
        if not self.checkIfUserLinked(id):
            embed= utility.generateLeagueFailedEmbed(text="Your discord account isn't linked to a league account, link with /linkleague", author=author, author_icon=url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if not self.checkIfUserLinked(friend_id):
            embed = utility.generateLeagueFailedEmbed(text="Your friend has not linked their league account, link with /linkleague", author=author, author_icon=url)
            await interaction.response.send_message(embed=embed)
            return
        friends:str = self.cursor.execute('SELECT friends From League WHERE did IS ?', (id)).fetchone()
        friend_list = friends.split('`')
        friends_summoner = self.cursor.execute('SELECT linked_league From League WHERE did IS ?',(friend_id)).fetchone()
        friend_list.remove(friends_summoner)
        friends = '`'.join(friend_list)
        self.cursor.execute('UPDATE League SET friends = ? WHERE did IS ?',(friends, id))
        self.database.commit()
        embed = utility.generateLeagueSuccessEmbed(f"Successfully removed {friends_summoner} from your friend list.", author, url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='addleague', description="Add a user to your league friends.")
    @app_commands.guilds(discord.Object(817238795966611466))
    async def addleague(self, interaction:discord.Interaction, friend:discord.User)->None:
        id = interaction.user.id
        author = interaction.user.display_name
        url = interaction.user.display_avatar.url
        friend_id = friend.id
        if not self.checkIfUserLinked(id):
            embed= utility.generateLeagueFailedEmbed(text="Your discord account isn't linked to a league account, link with /linkleague", author=author, author_icon=url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if not self.checkIfUserLinked(friend_id):
            embed = utility.generateLeagueFailedEmbed(text="Your friend has not linked their league account, link with /linkleague", author=author, author_icon=url)
            await interaction.response.send_message(embed=embed)
            return
        friends:str = self.cursor.execute('SELECT friends From League WHERE did IS ?', (id)).fetchone()
        friend_list = friends.split('`')
        friends_summoner = self.cursor.execute('SELECT linked_league From League WHERE did IS ?',(friend_id)).fetchone()
        friend_list.append(friends_summoner)
        friends = '`'.join(friend_list)
        self.cursor.execute('UPDATE League SET friends = ? WHERE did IS ?',(friends, id))
        self.database.commit()
        embed = utility.generateLeagueSuccessEmbed(f"Successfully added {friends_summoner} to your friend list.", author, url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='unlinkleague', description="Unlink your associated league account.")
    @app_commands.guilds(discord.Object(817238795966611466))
    async def unlinkleague(self, interaction:discord.Interaction):
        id = interaction.user.id
        display_name = interaction.user.display_name
        display_icon = interaction.user.display_avatar.url
        if not self.checkIfUserLinked(id):
            embed= utility.generateLeagueFailedEmbed("Your discord account isn't linked to a league account, link with /linkleague", display_name, display_icon)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        self.cursor.execute('UPDATE League SET linked_league = ? WHERE did IS ?',("",id))
        self.database.commit()
        embed = utility.generateLeagueSuccessEmbed("Successfully unlinked.", display_name, display_icon)
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name='linkleague', description='Link a league account to your discord.')
    @app_commands.guilds(discord.Object(817238795966611466))
    async def linkleague(self, interaction:discord.Interaction, summonername : str, region : str)->None:
        id = interaction.user.id
        if self.checkIfUserLinked(id):
            embed = utility.generateLeagueFailedEmbed("You already have a linked league account.", interaction.user.display_name, interaction.user.display_avatar.url)
            await interaction.response.send_message(embed=embed)
            return
        display_name = interaction.user.display_name
        display_icon = interaction.user.display_avatar.url
        if not utility.isValidLeagueRegion(region):
            embed = utility.generateLeagueFailedEmbed("The region entered is invalid, needs to be ['EUW','EUN','NA','OC','BR','JP', 'LA1', 'LA2', 'KR' or 'TR']",display_name,display_icon)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        converted_region = self.convertRegion(region.removeprefix('#').upper())
        summoner = self.watcher.summoner.by_name(converted_region, summonername)
        summonerName = summoner['name'] + '#' + converted_region
        self.cursor.execute('''UPDATE League SET 
        linked_league = ?,
        puuid = ?,
        id = ?,
        icon = ?,
        level = ?
        WHERE did IS ?''',(summonerName,summoner['puuid'],summoner['id'],summoner['profileIconId'],summoner['summonerLevel'],id,))
        self.database.commit()
        embed = utility.generateLeagueSuccessEmbed(f"Successfully linked {summoner['name']}#{converted_region} to your discord account.", display_name, display_icon)
        await interaction.response.send_message(embed=embed)

    @linkleague.autocomplete('region')
    async def linkerAutocomplete(self, interaction: discord.Interaction, current:str)->List[app_commands.Choice[str]]:
        regions = ['TR','RU','OC','EUN','JP','LA','KR','NA','EUW']
        return [
            app_commands.Choice(name=region, value=region)
            for region in regions if current.lower() in region.lower()
        ]
    ##### LEAGUE UTILITY #######

    async def matchViewCallback(self, view, index, emoji):
        for x in self.activeMatchHistories:
            if x[3] == view:
                currentView = view
                break
        

    def generateMatchesEmbed(self, matches, puuid, lid, author, url, match_embed_data):
        league_name:str = self.cursor.execute(f"SELECT linked_league FROM League WHERE did IS {match_embed_data[0]}").fetchone()[0]
        league_name = league_name.split('#')[0]
        embed = discord.Embed(title=f"{league_name}'s Matches", color=0x3d36cf, description="These overview stats surmise the last 50 games.")
        embed.set_author(name=f"{author}", icon_url=f'{url}')
        wins = 0
        losses = 0
        most_played_champ = {}
        most_played_role = {}
        kills = 0
        deaths = 0
        assists = 0
        for x in matches:
            player_data = self.getPlayerDataFromMatch(x['info'], lid)
            if self.getMatchResultFromPlayerData(player_data):
                wins += 1
            else:
                losses += 1
            role = self.getMatchRoleFromPlayerData(player_data)
            if role not in most_played_role:
                most_played_role[role] = 1
            else:
                most_played_role[role] += 1
            kda = self.getKillsDeathsAssistsFromPlayerData(player_data)
            kills += kda[0]
            deaths += kda[1]
            assists += kda[2]
            champName = self.getChampNameFromPlayerData(player_data)
            if champName not in most_played_champ:
                most_played_champ[champName] = 1
            else:
                most_played_champ[champName] += 1
        if wins >= losses:
            emoteurl = self.positiveEmotes[randrange(0,len(self.positiveEmotes))].removesuffix('\n')
        else:
            emoteurl = self.negativeEmotes[randrange(0,len(self.negativeEmotes))].removesuffix('\n')
        embed.set_thumbnail(url=self.emoteUrl+emoteurl)
        most_played_role.pop("Invalid", "")
        top_role = max(most_played_role, key=most_played_role.get)
        top_champ = max(most_played_champ, key=most_played_champ.get)
        embed.add_field(name='Kills <:among_us_dead:784255946326671372>',value=f"""```ini\n[ {kills} ]\n```""")
        embed.add_field(name='Deaths <:what:812713040881385492>',value=f"""```ini\n[ {deaths} ]\n```""")
        embed.add_field(name='Assists <:greetings:366157822481924106>',value=f"""```ini\n[ {assists} ]\n```""")
        embed.add_field(name='Wins <:StonksCypher:932829442299031582>',value=f"""```yaml\n[ {wins} ]\n```""")
        winrate = (float(wins)/50.0)*100.0
        if winrate > 50.0:
            embed.add_field(name='W/R <:dab:499726833890230273>',value=f"```asciidoc\n= {(float(wins)/50.0)*100.0}% =\n```")
        else:
            embed.add_field(name=f'W/R <:youtried:596576824872402974>',value=f"```asciidoc\n= >{(float(wins)/50.0)*100.0}%< =\n```")

        embed.add_field(name='<:PepePoint:759934591590203423> Losses',value=f"""```asciidoc\n[ {losses} ]\n```""")
        embed.add_field(name='<:whenyahomiesaysomewildshit:596577153135673344> Top Role', value=f"""```md\n< {top_role} >\n```""")
        embed.add_field(name='\u200b',value="\u200b")
        embed.add_field(name='Top Champ <:POGGERS:467444095053201410>', value=f"""```md\n< {top_champ} >\n```""")
        return embed

    def getChampNameFromPlayerData(self, player_data):
        return player_data['championName']

    def getKillsDeathsAssistsFromPlayerData(self, player_data):
        kills = player_data['kills']
        deaths = player_data['deaths']
        assists = player_data['assists']
        return [kills,deaths,assists]

    def getMatchRoleFromPlayerData(self, player_data):
        if player_data['teamPosition'] == '' or player_data['teamPosition'] == ' ':
            return "Invalid"
        return player_data['teamPosition']

    def getMatchResultFromPlayerData(self, player_data):
        return player_data['win']

    def generateFriendsEmbed(self, id, list:List[str], author,url):
        league_name:str = self.cursor.execute(f"SELECT linked_league FROM League WHERE did IS {id}").fetchone()[0]
        league_name = league_name.split('#')[0]
        embed = discord.Embed(title=f"{league_name}'s Friends", color=0xcf3a61)
        embed.set_author(name=f"{author}", icon_url=f'{url}')
        embed.set_thumbnail(url=f'{league_content_url}friends_icon.png')
        names = '\u200b'
        gameinfo = '\u200b'
        for x in list:
            id = self.getID(x)
            display_name = x.removesuffix('1').removesuffix('2')
            if (len(display_name) > 15):
                names += display_name[:15] + '...\n'
            else:
                names += display_name + '\n'
            region = display_name.split('#')[1]
            player_game_info = self.getCurrentGameInfo(region,id)
            if player_game_info == None:
                gameinfo += 'Not In-Game\n'
                continue
            player_info = self.getPlayerDataFromMatch(player_game_info, id)
            player_character = self.getCharacterInGame(player_info)
            gameinfo += player_character
            match_elapsed = self.getMatchElapsed(player_game_info)
            gameinfo += f'{match_elapsed}\n'
        embed.add_field(name='Friend',value=names)
        embed.add_field(name='Game Info',value=gameinfo)
        return embed

    def getMatchElapsed(self, game_info):
        startTimeS = game_info['gameStartTime'] / 1000
        nowS = time.time()
        return utility.secondsToMinSecString(nowS - startTimeS)

    def getCharacterInGame(self, player_info):
        for x in self.champList['data'].values():
            if int(x['key']) == player_info['championId']:
                return x['id']
        return None

    def getPlayerDataFromMatch(self, game_info, id):
        playersInGame = game_info['participants']
        for x in playersInGame:
            if x['summonerId'] == id:
                return x
        return None 

    def getCurrentGameInfo(self, region, id):
        matchRegion = self.getMatchRegionFromUserRegion(region)
        try:
            matchInfo = self.watcher.spectator.by_summoner(matchRegion, id)
        except:
            return None
        return matchInfo

    def getMatchRegionFromUserRegion(self, region):
        asian = ['OC','JP','KR']
        american = ['LA','NA']
        european = ['EUW','EUN','RU','TR']
        if asian.__contains__(region):
            return "ASIA"
        if american.__contains__(region):
            return "AMERICAS"
        if european.__contains__(region):
            return "EUROPE"
        return None

    def getID(self, name : str):
        #name = name.removesuffix('1').removesuffix('2')
        summoner = name.split('#')
        return self.watcher.summoner.by_name(summoner[1], summoner[0])['id'] 

    def convertRegion(self, region):
        if region == 'KR' or region == 'RU':
            return region
        if region =='LA2' or region =='LA1':
            return region
        return region + '1' 

    def checkIfUserLinked(self, id):
        self.ensureUserInDatabase(id)
        record = self.cursor.execute(f'SELECT * FROM League WHERE did IS {id}').fetchone()
        if record[1] == None:
            return False
        return True

    def ensureUserInDatabase(self,id):
        record = self.cursor.execute(f'SELECT * FROM League WHERE did IS {id}').fetchone()
        if record == None:
            self.cursor.execute(f'''INSERT INTO League VALUES ({id},?,?,?,?,?,?,?)''', (None,None,None,None,"",None,""))
            self.database.commit()

    ############################

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(League(bot))
