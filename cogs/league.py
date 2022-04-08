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
    @app_commands.guilds(discord.Object(600696326287785984))
    async def leaguematches(self, interaction:discord.Interaction)->None:
        if self.checkUserAlreadyAskedForMatch(interaction.user.id):
            await interaction.response.send_message("You have an active match board still.")
            return
        await interaction.response.defer()
        id = interaction.user.id
        author = interaction.user.display_name
        url = interaction.user.display_avatar.url
        if not self.checkIfUserLinked(id):
            embed= utility.generateLeagueFailedEmbed("Your discord account isn't linked to a league account, link with /linkleague", author, url)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        userdata = self.cursor.execute("SELECT * FROM League WHERE did is ?",(id,)).fetchone()
        league_name:str = userdata[1]
        league_puuid = userdata[2]
        league_id = userdata[3]
        regionNoNumber = league_name.split('#')[1].removesuffix('1').removesuffix('2')
        match_region = self.getMatchRegionFromUserRegion(regionNoNumber)
        player_matches_ids = self.watcher.match.matchlist_by_puuid(match_region, league_puuid, count=50)
        player_matches = []
        for i in player_matches_ids:
            player_matches.append(self.watcher.match.by_id(match_region, i))
        embed_data = [id,0,9]
        embed_data.append(None)
        embed_data.append(player_matches)
        embed_data.append(league_id)
        embed_data.append(author)
        embed_data.append(url)
        embed = self.generateMatchesEmbed(embed_data)
        view = LeagueMatchView(embed_data, self)
        embed_data.insert(3,view)
        embed_data.remove(None)
        self.activeMatchHistories.append(embed_data)
        await interaction.followup.send(embed=embed, view=view)
        #await interaction.response.send_message(embed=embed,view=view)

    @app_commands.command(name='leaguefriends',description="List your friends and their current games.")
    @app_commands.guilds(discord.Object(600696326287785984))
    async def leaguefriends(self, interaction:discord.Interaction)->None:
        id = interaction.user.id
        author = interaction.user.display_name
        url = interaction.user.display_avatar.url
        if not self.checkIfUserLinked(id):
            embed= utility.generateLeagueFailedEmbed(text="Your discord account isn't linked to a league account, link with /linkleague", author=author, author_icon=url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        friends_list = self.cursor.execute(f'SELECT friends FROM League WHERE did is {id}').fetchone()[0]
        if len(friends_list) == 0:
            await interaction.response.send_message("You have no friends added, add some with /addleague", ephemeral=True)
            return
        friends_list = friends_list.split('`')
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
    @app_commands.guilds(discord.Object(600696326287785984))
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
        friends:str = self.cursor.execute('SELECT friends From League WHERE did IS ?', (id,)).fetchone()[0]
        friend_list = friends.split('`')
        friends_summoner = self.cursor.execute('SELECT linked_league From League WHERE did IS ?',(friend_id,)).fetchone()
        friend_list.remove(friends_summoner)
        friends = '`'.join(friend_list).removeprefix('`')
        self.cursor.execute('UPDATE League SET friends = ? WHERE did IS ?',(friends, id,))
        self.database.commit()
        embed = utility.generateLeagueSuccessEmbed(f"Successfully removed {friends_summoner} from your friend list.", author, url)[0]
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='addleague', description="Add a user to your league friends.")
    @app_commands.guilds(discord.Object(600696326287785984))
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
        friends = self.cursor.execute('SELECT friends From League WHERE did IS ?', (id,)).fetchone()[0]
        friend_list = friends.split('`')
        friends_summoner = self.cursor.execute('SELECT linked_league From League WHERE did IS ?',(friend_id,)).fetchone()[0]
        friend_list.append(friends_summoner)
        friends = '`'.join(friend_list).removeprefix('`')
        self.cursor.execute('UPDATE League SET friends = ? WHERE did IS ?',(friends, id,))
        self.database.commit()
        embed = utility.generateLeagueSuccessEmbed(f"Successfully added {friends_summoner} to your friend list.", author, url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='unlinkleague', description="Unlink your associated league account.")
    @app_commands.guilds(discord.Object(600696326287785984))
    async def unlinkleague(self, interaction:discord.Interaction):
        id = interaction.user.id
        display_name = interaction.user.display_name
        display_icon = interaction.user.display_avatar.url
        if not self.checkIfUserLinked(id):
            embed= utility.generateLeagueFailedEmbed("Your discord account isn't linked to a league account, link with /linkleague", display_name, display_icon)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        self.cursor.execute('UPDATE League SET linked_league = ? WHERE did IS ?',(None,id))
        self.database.commit()
        embed = utility.generateLeagueSuccessEmbed("Successfully unlinked.", display_name, display_icon)
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name='linkleague', description='Link a league account to your discord.')
    @app_commands.guilds(discord.Object(600696326287785984))
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

    def removeMatchList(self, view):
        for x in self.activeMatchHistories:
            if x[3] == view:
                self.activeMatchHistories.remove(x)
                return

    def checkUserAlreadyAskedForMatch(self, id):
        for x in self.activeMatchHistories:
            if x[0] == id:
                return True
        return False

    async def matchViewCallback(self, view, interaction : discord.Interaction,index, emoji):
        for x in self.activeMatchHistories:
            if x[3] == view:
                embed_data = x
                break
        if embed_data == None:
            raise AssertionError("View was not found in the active match history")
        if emoji == '↪️':
            emoji = None
        if index == -1:
            if emoji.name == '⬅️':
                if embed_data[1] == 0:
                    return 
                embed_data[1] -= 9
                embed_data[2] -= 9
            elif emoji.name == '➡️':
                if embed_data[2] >= len(embed_data[4]):
                    return
                embed_data[1] += 9
                embed_data[2] += 9
            embed = self.generateMatchesEmbed(embed_data)
            embed_data[3].enableNav()
            await interaction.response.edit_message(embed=embed,view=embed_data[3])
        elif emoji == None:
            embed = self.generateDetailedMatch(embed_data, (embed_data[1] + index-1))
            embed_data[3].disableNav()
            await interaction.response.edit_message(embed=embed,view=embed_data[3])

    def generateDetailedMatch(self, embed_data, index):
        league_name = self.cursor.execute(f"SELECT linked_league FROM League WHERE did IS {embed_data[0]}").fetchone()[0]
        league_name = league_name.split('#')[0]
        game_info = embed_data[4][index]['info']
        player_data = self.getPlayerDataFromMatch(game_info,embed_data[5])
        champName = self.getChampNameFromPlayerData(player_data)
        win = self.getMatchResultFromPlayerData(player_data)
        if win:
            colour = 0x32cf54
        else:
            colour = 0xcf3242
        gm = self.getGameModeFromMatch(game_info).capitalize()
        durataion = utility.secondsToMinSecString(game_info['gameDuration'])
        embed = discord.Embed(title=f"{gm} - {durataion}", color=colour)
        embed.set_author(name=f'{league_name} as {champName}')
        embed.set_thumbnail(url=f'{self.champUrl}{champName}.png')
        role = self.getMatchRoleFromPlayerData(player_data)
        roleEmoji = self.getRoleEmoji(role)
        kda = self.getKillsDeathsAssistsFromPlayerData(player_data)
        if kda[1] == 0:
            kda[1] = 1
        kda = '{:.2}'.format((kda[0] + kda[2]) / kda[1])
        gold = self.getGoldFromPlayerData(player_data)
        dmgDoneChampions = self.getDamageToChampsFromPlayerData(player_data)
        mitigated = self.getMitigatedFromPlayerData(player_data)
        healed = self.getHealedFromPlayerData(player_data)
        dynamic_stat = self.getHighestKill(player_data)
        turretDmg = None
        if dynamic_stat is None:
            turretDmg = True
            dynamic_stat = self.getTurretDamage(player_data)
        cc = self.getCCScoreFromPlayerData(player_data)
        vision = self.getVisionScore(player_data)
        ff = self.getFF(player_data)
        primaryRune = self.getPrimaryRune(player_data)
        secondaryTree = self.getSecondaryRuneTree(player_data)
        embed.add_field(name=f'Role{roleEmoji}', value=f'{role}')
        embed.add_field(name='KDA ⚰️', value=f'{kda}')
        embed.add_field(name='Gold',value=f'<:gold:962089056651608155> {gold}')
        embed.add_field(name='Champ Dmg', value=f'{dmgDoneChampions}<:3655soypoint:962099404024737793>')
        embed.add_field(name='Dmg Tanked <:SCIron:929123285470437376>', value=f'{mitigated}')
        embed.add_field(name='Dmg Healed <:blobpats:596576796594667521>', value=f'{healed}')
        if turretDmg is not None:
            embed.add_field(name='Tower Dmg <:blobban:759935431847968788>', value=f'{dynamic_stat}')
        else:
            embed.add_field(name=f'{dynamic_stat[0]}<a:froggydefault:744347632754884639>',value=f'{dynamic_stat[1]}') 
        embed.add_field(name='CC <:stickbug:744346789863358505>',value=f'{cc}')
        embed.add_field(name='Vision 👀',value=f'{vision}')
        embed.add_field(name='<:hmm:784328449439039518> FF?', value=f'{ff}')
        embed.add_field(name='1° Rune',value=f'{primaryRune}')
        embed.add_field(name='2° Tree',value=f'{secondaryTree}')
        return embed

    def getRoleEmoji(self,role):
        if role == 'Top':
            return '<:Top:962099404339306596>'
        elif role == 'Support':
            return '<:Support:962099404242841620>'
        elif role == 'Jungle':
            return '<:Jungle:962099404104409119>'
        elif role == 'Bottom':
            return '<:Bottom:962099404578365480>'
        elif role == 'Middle':
            return '<:Middle:962099404297351238>'
        return '<:what:812713040881385492>'

    def getSecondaryRuneTree(self,player_data):
        perkSecondaryStyle = player_data['perks']['styles'][1]['style']
        if perkSecondaryStyle == 8100:
            return "Domination"
        elif perkSecondaryStyle == 8300:
            return "Inspiration"
        elif perkSecondaryStyle == 8000:
            return "Precision"
        elif perkSecondaryStyle == 8400:
            return "Resolve"
        elif perkSecondaryStyle == 8200:
            return "Sorcery"
        return '<:press_F:911697562518585344>'

    def getPrimaryRune(self,player_data):
        playersRune = player_data['perks']['styles'][0]['selections'][0]['perk']
        for tree in self.runesList:
            for slot in tree['slots']:
                for runes in slot['runes']:
                    if runes['id'] == playersRune:
                        return runes['key']
        return '<:press_F:911697562518585344>'

    def getFF(self, player_data):
        return player_data['gameEndedInSurrender']

    def getVisionScore(self,player_data):
        return player_data['visionScore']

    def getCCScoreFromPlayerData(self,player_data):
        return player_data['timeCCingOthers']

    def getTurretDamage(self, player_data):
        return player_data['damageDealtToTurrets']

    def getHighestKill(self,player_data):
        if player_data['pentaKills'] > 0:
            return ['Pentas',player_data['pentaKills']]
        elif player_data['quadraKills'] > 0:
            return ['Quadras', player_data['quadraKills']]
        elif player_data['tripleKills'] > 0:
            return ['Triples',player_data['tripleKills']]
        return None

    def getHealedFromPlayerData(self,player_data):
        return player_data['totalHeal']

    def getMitigatedFromPlayerData(self, player_data):
        return player_data['damageSelfMitigated']

    def getDamageToChampsFromPlayerData(self, player_data):
        return player_data['totalDamageDealtToChampions']

    def getGoldFromPlayerData(self, player_data):
        return player_data['goldEarned']

    def generateMatchesEmbed(self, embed_data):
        ## MATCH DATA : 0=DID, 1=START, 2=END, 3=VIEW, 4=MATCHES, 5=LEAGUEID, 6=DISPLAYNAME, 7=DISPLAYAVATARURL
        league_name:str = self.cursor.execute(f"SELECT linked_league FROM League WHERE did IS {embed_data[0]}").fetchone()[0]
        league_name = league_name.split('#')[0]
        embed = discord.Embed(title=f"{league_name}'s Matches", color=0x3d36cf, description="These overview stats surmise the last 50 games.")
        embed.set_author(name=f"{embed_data[6]}", icon_url=f'{embed_data[7]}')
        wins = 0
        losses = 0
        most_played_champ = {}
        most_played_role = {}
        kills = 0
        deaths = 0
        assists = 0
        for x in embed_data[4]:
            player_data = self.getPlayerDataFromMatch(x['info'], embed_data[5])
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
        embed.add_field(name='Wins <:3487jhinstonks4:962099404100223057>',value=f"""```yaml\n[ {wins} ]\n```""")
        winr = (float(wins)/len(embed_data[4]))*100.0
        good_winrate = winr > 50.0
        winrate = "{:.1f}".format(winr)
        if good_winrate:
            embed.add_field(name='W/R <:dab:499726833890230273>',value=f"```asciidoc\n= {winrate}% =\n```")
        else:
            embed.add_field(name=f'W/R <:youtried:596576824872402974>',value=f"```asciidoc\n= >{winrate}%< =\n```")

        embed.add_field(name='<:PepePoint:759934591590203423> Losses',value=f"""```asciidoc\n[ {losses} ]\n```""")
        embed.add_field(name='<:whenyahomiesaysomewildshit:596577153135673344> Top Role', value=f"""```md\n< {top_role} >\n```""")
        embed.add_field(name='\u200b',value="\u200b")
        embed.add_field(name='Top Champ <:POGGERS:467444095053201410>', value=f"""```md\n< {top_champ} >\n```""")
        self.addMatchInfoToEmbed(embed_data[5], embed, embed_data[4][embed_data[1]:embed_data[2]])
        return embed

    def addMatchInfoToEmbed(self,lid,embed : discord.Embed, matches):
        for x in matches:
            matchInfo = x['info']
            gameLength = matchInfo['gameDuration']
            gameLength = utility.secondsToMinSecString(int(gameLength))
            player_data = self.getPlayerDataFromMatch(matchInfo, lid)
            champName = self.getChampNameFromPlayerData(player_data)
            gameMode = self.getGameModeFromMatch(matchInfo)
            if gameMode == 'ARAM':
                gmEmote = '<:aram:962065966257283093>'
            elif gameMode == 'SR':
                gmEmote = '<:sr:962065976214577203>'
            else:
                gmEmote = '<:featured:962065989208531014>'
            if self.getMatchResultFromPlayerData(player_data):
                winEmote = '<:GreatlyIncreased:932827416722829455>'
            else:
                winEmote = '<:GreatlyDecreased:932827435202928710>'
            embed.add_field(name=f"{winEmote} {champName} {gmEmote}", value=f"{gameLength}")

    def getGameModeFromMatch(self, matchInfo):
        gm = matchInfo['gameMode']
        if gm == 'ARAM':
            return 'ARAM'
        elif gm == 'CLASSIC':
            return 'SR'
        return 'FEATURED'

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
        if player_data['teamPosition'] == 'UTILITY':
            return 'Support'
        return player_data['teamPosition'].capitalize()

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
