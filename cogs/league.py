import discord,secrets, math, json, asyncio, sqlite3, utility, time
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
        self.activeQueries = []
        self.watcher : LolWatcher = LolWatcher(secrets.leagueKey)
        versions = self.watcher.data_dragon.versions_for_region('euw')
        self.baseRankUrl = "https://thebestcomputerscientist.co.uk/leagueranks/Emblem_"
        self.champList = self.watcher.data_dragon.champions(versions['n']['champion'])
        self.iconList = self.watcher.data_dragon.profile_icons(versions['n']['profileicon'])
        self.summonerList = self.watcher.data_dragon.summoner_spells(versions['n']['summoner'])
        self.runesList = self.watcher.data_dragon.runes_reforged(versions['n']['profileicon'])
        self.iconUrl = f"https://ddragon.leagueoflegends.com/cdn/{versions['n']['profileicon']}/img/profileicon/"
        self.champUrl = f"https://ddragon.leagueoflegends.com/cdn/{versions['n']['profileicon']}/img/champion/"

    @app_commands.command(name='leaguematches',description="List your recent League games.")
    @app_commands.guilds(discord.Object(817238795966611466))
    async def leaguefriends(self, interaction:discord.Interaction)->None:
        id = interaction.user.id
        author = interaction.user.display_name
        url = interaction.user.display_avatar.url
        if not self.checkIfUserLinked(id):
            embed= utility.generateLeagueFailedEmbed(text="Your discord account isn't linked to a league account, link with /linkleague", author=author, author_icon=url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        userdata = self.cursor.execute("SELECT * FROM League WHERE did is ?",(id,)).fetchone()
        league_name = userdata[1]
        league_puuid = userdata[2]
        match_region = self.getMatchRegionFromUserRegion(league_name.split('#')[1])
        player_matches_ids = self.watcher.match.matchlist_by_puuid(match_region, league_puuid, count=50)
        player_matches = []
        for i in player_matches_ids:
            player_matches.append(self.watcher.match.by_id(match_region, player_matches_ids[i]))
        
        
        


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
