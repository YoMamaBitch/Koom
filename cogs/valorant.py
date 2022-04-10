import json
import discord,secrets, utility, urllib.request, urllib.parse, hashlib

from numpy import character
from riotwatcher import ValWatcher, RiotWatcher
from discord.ext import commands
from discord import app_commands
from valorant_view import ValorantMatchView

class Valorant(commands.Cog):
    def __init__(self,bot:commands.Bot)->None:
        self.bot = bot 
        self.riotwatcher = RiotWatcher(secrets.valKey)
        self.watcher = ValWatcher(secrets.valKey)
        self.activeMatches = []
        self.playerCardUrl = 'https://media.valorant-api.com/playercards/'
        self.agentImageUrl = 'https://media.valorant-api.com/agents/'
        self.compTiers = {0:'Unranked',3:'Iron I',4:'Iron II',5:'Iron III',6:'Bronze I',7:'Bronze II',8:'Bronze III',
        9:'Silver I',10:'Silver II',11:'Silver III',12:'Gold I',13:'Gold II',14:'Gold III',15:'Platinum I',16:'Platinum II',
        17:'Platinum III',18:'Diamond I',19:'Diamond II',20:'Diamond III',21:'Immortal I',22:'Immortal II', 23:'Immortal III', 24:'Radiant'}
        self.initialiseContent()
        self.initialiseMaps()

    
    @app_commands.command(name='valorantmatches',description='Unlink your valorant account from discord.')
    @app_commands.guilds(discord.Object(817238795966611466))
    async def valorantmatches(self, interaction:discord.Interaction)->None:
        id = interaction.user.id
        author_name = interaction.user.display_name
        avatar_url = interaction.user.display_avatar.url
        self.ensureUserInDatabase(id)
        if not self.userAuthenticated(id):
            await interaction.response.send_message("You have not been authenticated, use /linkvalorant.")
            return
        await interaction.response.defer(thinking=True)
        userdata = utility.cursor.execute('SELECT * FROM Valorant WHERE did IS ?',(id,)).fetchone()
        puuid = userdata[3]
        matchlist = self.watcher.match.matchlist_by_puuid('EU', puuid)['history']
        match1 = self.watcher.match.by_id('EU',matchlist[0]['matchId'])
        player_card = self.getPlayerCardFromMatch(match1, puuid)
        matches = [match1]
        embed_data = {'id':id, 'start':0, 'end':5, 'matches':matches, 'matchlist':matchlist,
                    'puuid':puuid, 'display_name':author_name, 'display_url':avatar_url, 'playercard':player_card,
                    'matchIndex':0, 'roundIndex':0}
        view = ValorantMatchView(embed_data, self)
        embed_data['view'] = view
        embed = self.generateMatchOverview(embed_data)
        self.activeMatches.append(embed_data)
        await interaction.followup.send(embed=embed,view=view)

    @app_commands.command(name='unlinkvalorant',description='Unlink your valorant account from discord.')
    @app_commands.guilds(discord.Object(817238795966611466))
    async def unlinkvalorant(self, interaction:discord.Interaction)->None:
        id = interaction.user.id
        self.ensureUserInDatabase(id)
        userdata = utility.cursor.execute("SELECT * FROM Valorant WHERE did IS ?",(id,)).fetchone()
        authenticated = userdata[2]
        if authenticated == 0:
            await interaction.response.send_message("You're already un-authenticated.", ephemeral=True)
            return
        userdata[2] = False
        utility.cursor.execute("UPDATE Valorant SET authenticated = 0 WHERE did IS ?",(id,))
        utility.database.commit()
        await interaction.response.send_message(content="Your valorant account has been unlinked.", ephemeral=True)

    @app_commands.command(name='linkvalorant',description='Link your valorant account to discord using RSO.')
    @app_commands.guilds(discord.Object(817238795966611466))
    async def linkvalorant(self, interaction:discord.Interaction)->None:
        id = interaction.user.id
        self.ensureUserInDatabase(id)
        userdata = utility.cursor.execute("SELECT * FROM Valorant WHERE did IS ?",(id,)).fetchone()
        authenticated = userdata[2]
        if authenticated == 1:
            await interaction.response.send_message("You're already authenticated.", ephemeral=True)
            return
        hashed_id = self.getHashedId(id)
        hashed_id = urllib.parse.quote_plus(hashed_id)
        url = f"https://thebestcomputerscientist.co.uk/html/koom-request.html?id={hashed_id}"
        embed = discord.Embed(title="Valorant Authentication", color=0xd62c20, url=url)
        embed.set_footer(text="Do not share the attached link with anyone")
        await interaction.user.send(embed=embed)
        await interaction.response.send_message("You have been DM'd an authentication link. Ask Keiron to switch the server on to listen for your authentication.",ephemeral=True)

    @commands.command(name='pullcontent')
    async def pullcontent(self, ctx):
        if ctx.author.id != secrets.keironID:
            return
        try:
            content = self.watcher.content.contents('NA','en-GB')
        except:
            await ctx.send("Content server offline, try later bro")
            return
        self.content = content
        self.loadAbilities()
        self.saveJson('localValorantContent/content.json', self.content)
        await ctx.send("Updated successfully.")

    ######### UTILITY ###################

    def generateMatchOverview(self, embed_data):
        #0 = did, 1 = start, 2=end,3=matches,4=matchlist,5=puuid,6=author_name,7=avatar_url,8=playercard,9=view, 10 = round
        #Blue always defend first
        gamename = self.getUserName(embed_data['puuid'])
        playercardUrl = self.playerCardUrl + embed_data['playercard'] + '/smallart.png'
        embed = discord.Embed(title=f'Recent Matches',color=0x1aba9f)
        playerRank = self.getPlayerRankFromMatch(embed_data['matches'][0],embed_data['puuid'])
        embed.set_author(name=f"{embed_data['display_name']}", icon_url=f"{embed_data['display_url']}")
        #embed.set_thumbnail(url=playercardUrl)
        embed.set_image(url=f"{self.playerCardUrl}{embed_data['playercard']}/wideart.png")
        embed.set_footer(text=f"{gamename} : {playerRank}")
        while len(embed_data['matches']) < embed_data['end']+1:
            matchId = embed_data['matchlist'][len(embed_data['matches'])]
            embed_data['matches'].append(self.watcher.match.by_id('EU',matchId['matchId']))         
        for i in range(embed_data['start'], embed_data['end']+1):
            agent = self.getAgentFromMatch(embed_data['matches'][i], embed_data['puuid'])
            mapName = self.getMapNameFromMatch(embed_data['matches'][i])
            gameLengthStr = self.getMatchLength(embed_data['matches'][i])
            embed.add_field(name=f'{i+1} - {agent}', value=f'```yaml\n{mapName}: {gameLengthStr}\n```')
        return embed

    async def matchViewCallback(self, view : ValorantMatchView, interaction:discord.Interaction, text,emoji):
        embed_data = view.match_embed_data
        if text is not None and emoji is None:
            embed_data['matchIndex'] = int(text) - 1 + embed_data['start']
            match_data = embed_data['matches'][embed_data['matchIndex']]
            embed = self.generateMatchEmbed(match_data, embed_data['display_name'], 
                    embed_data['display_url'], embed_data['playercard'], embed_data['puuid'])
            view.enableMatch()
            await interaction.response.send_message(embed=embed, view=view)
            return
        
        view.enableOverview()
        embed = self.generateMatchOverview(view.match_embed_data)
        await interaction.response.send_message(embed=embed,view=view)

    def generateMatchEmbed(self, match_data, display_name, display_icon, playercard, puuid):
        mapName = self.getMapNameFromMatch(match_data)
        win = self.getMatchResult(match_data, puuid)
        if win:
            color = 0x25c242
        else:
            color = 0xd6392b
        embed = discord.Embed(title=mapName, color=color)
        embed.set_author(name=display_name, icon_url=display_icon)
        team = self.getPlayerTeamFromMatch(match_data,puuid)
        party = self.getPlayerPartyFromMatch(match_data,puuid)
        playerData = self.getPlayerDataFromMatch(match_data, puuid)
        characterId = playerData['characterId']
        characterUrl = self.agentImageUrl + characterId.lower() + '/displayicon.png'
        embed.set_thumbnail(url=characterUrl)
        kills = self.getPlayerKillsFromMatch(match_data, puuid)
        deaths = self.getPlayerDeathsFromMatch(match_data, puuid)
        assists = self.getPlayerAssistsFromMatch(match_data,puuid)
        favouriteWeapon = self.getFavouriteWeaponFromMatch(match_data,puuid)
        abilityUses = self.getPlayerAbilityUsageFromMatch(match_data, puuid)
        embed.add_field(name='Kills',value=f'```yaml\n{kills}\n```')
        embed.add_field(name='Deaths',value=f'```yaml\n{deaths}\n```')
        embed.add_field(name='Assists',value=f'```yaml\n{assists}\n```')
        embed.add_field(name='Fav. Weapon',value=f'```yaml\n{favouriteWeapon}\n```',inline=False)
        abilityCodeBlock = f'```yaml\n'
        for key in abilityUses.keys():
            abilityCodeBlock += f'{key} : {abilityUses[key]}\n'
        abilityCodeBlock += '```'
        embed.add_field(name="Ability Usage",value=abilityCodeBlock,inline=False)
        return embed

    def getMatchLength(self, match):
        lengthMs = match['matchInfo']['gameLengthMillis']
        return utility.secondsToMinSecString(int(lengthMs / 1000))

    def removeMatchList(self, embed_data):
        for x in self.activeMatches:
            if x == embed_data:
                self.activeMatches.remove(x)
                return

    def getMatchResult(self, match_data, puuid):
        playerTeam = self.getPlayerTeamFromMatch(match_data, puuid)
        for team in match_data['teams']:
            if team['won']:
                return playerTeam == team['teamId']
        return None

    def getFavouriteWeaponFromMatch(self,match_data,puuid):
        roundData = self.getMatchRounds(match_data)
        weapon_uses = {}
        for round in roundData:
            player_stats = self.getPlayerStatsFromRound(round,puuid)
            weaponId = player_stats['economy']['weapon']
            weaponName = self.weaponIdToName(weaponId)
            if weaponName not in weapon_uses:
                weapon_uses[weaponName] = 1
            else:
                weapon_uses[weaponName] += 1
        return max(weapon_uses, key=weapon_uses.get)

    def weaponIdToName(self, weaponId):
       for x in self.content['equips']:
           if x['id'].upper() == weaponId.upper():
               return x['name']

    def getPlayerStatsFromRound(self, round,puuid):
        stats= round['playerStats']
        for x in stats:
            if x['puuid'] == puuid:
                return x

    def getMatchRounds(self, match_data):
        return match_data['roundResults']

    def getMapNameFromMatch(self,match):
        maps = self.content['maps']
        for x in maps:
            if x.get('assetPath') == None:
                continue
            if match['matchInfo']['mapId'] == x['assetPath']:
                return x['name']

    def getUserName(self,puuid):
        account = self.riotwatcher.account.by_puuid('EUROPE',puuid)
        return account['gameName'] + '#' + account['tagLine']

    def userAuthenticated(self,id):
        entry = self.ensureUserInDatabase(id)
        return entry[2] == 1

    def getPlayerAbilityUsageFromMatch(self, match,puuid):
        playerData = self.getPlayerDataFromMatch(match,puuid)
        abilityCasts = playerData['stats']['abilityCasts']
        for x in self.content['characters']:
            if x['id'].upper() == playerData['characterId'].upper():
                ability1Name = x['abilities'][0]['displayName'].title()
                ability2Name = x['abilities'][1]['displayName'].title()
                grenadeName = x['abilities'][2]['displayName'].title()
                ultName = x['abilities'][3]['displayName'].title()
                break
        return {ability1Name:abilityCasts['ability1Casts'], ability2Name:abilityCasts['ability2Casts'],
                grenadeName:abilityCasts['grenadeCasts'], ultName:abilityCasts['ultimateCasts']}
                
    def isPlayerAttackOrDefend(self, match, puuid, round):
        team = self.getPlayerTeamFromMatch(match,puuid)
        if (team == 'Blue' and round < 12) or (team=='Red' and round >= 12):
            return 'Defense'
        return 'Attack'

    def getPlayerTeamFromMatch(self, match,puuid):
        playerdata = self.getPlayerDataFromMatch(match,puuid)
        return playerdata['teamId']

    def getAgentFromMatch(self, match, puuid):
        playerData = self.getPlayerDataFromMatch(match ,puuid)
        characterId = playerData['characterId']
        for x in self.content['characters']:
            if x['id'].lower() == characterId.lower():
                return x['name']

    def getPlayerAssistsFromMatch(self, match,puuid):
        playerData = self.getPlayerDataFromMatch(match,puuid)
        return playerData['stats']['assists']

    def getPlayerDeathsFromMatch(self, match,puuid):
        playerData = self.getPlayerDataFromMatch(match,puuid)
        return playerData['stats']['deaths']

    def getPlayerKillsFromMatch(self, match,puuid):
        playerData = self.getPlayerDataFromMatch(match,puuid)
        return playerData['stats']['kills']
    
    def getPlayerPartyFromMatch(self, match,puuid):
        players = match['players']
        partyId = self.getPlayerDataFromMatch(match,puuid)['partyId']     
        party = []
        for p in players:
            if p['partyId'] == partyId:
                party.append([p['gameName'],p['playerCard'],p['playerTitle'],p['competitiveTier']])
        return party

    def getPlayerTitleFromMatch(self, match,puuid):
        titleId = self.getPlayerDataFromMatch(match,puuid)['playerTitle']     
        for x in self.content['playerTitles']:
            if x['id'].lower() == titleId.lower():
                return x['name'].removesuffix('Title')

    def getPlayerRankFromMatch(self, match, puuid):
        tier = self.getPlayerDataFromMatch(match,puuid)['competitiveTier']
        return self.compTiers[tier]

    def getPlayerCardFromMatch(self, match, puuid):
        return self.getPlayerDataFromMatch(match,puuid)['playerCard']
    
    def getPlayerDataFromMatch(self, match,puuid):
        players = match['players']
        for p in players:
            if p['puuid'] == puuid:
                return p

    def getHashedId(self,id):
        hasher = hashlib.sha256()
        data_bytes = bytes(str(id), 'utf-8')
        hasher.update(data_bytes)
        hashed_id = hasher.digest()
        hashed_id = str(hashed_id)
        return hashed_id

    def checkIfUserLinked(self,id):
        entry = self.ensureUserInDatabase(id)
        if entry is None:
            utility.cursor.execute('''INSERT INTO Valorant 
            VALUES(?,?,?,?,?,?,?,?)''', (id,None,0,None,None,None,None,None,))
            return False
        if entry[2] == 1:
            return True
        return False
    
    def ensureUserInDatabase(self,id):
        entry = utility.cursor.execute("SELECT * FROM Valorant WHERE did IS ?",(id,)).fetchone()
        if entry is None:
            utility.cursor.execute('''INSERT INTO Valorant 
            VALUES(?,?,?,?,?,?,?,?)''', (id,None,0,None,None,None,None,None,))
            utility.database.commit()
            return [id,None,0,None,None,None,None,None]
        return entry

    def checkContentForAbilities(self):
        if self.content['characters'][0].get('abilities') == None:
            self.loadAbilities()
            self.saveJson('localValorantContent/content.json', self.content)

    def saveJson(self, path, json):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(json))

    def loadAbilities(self):
        url = 'https://valorant-api.com/v1/agents/'
        for x in self.content['characters']:
            id = x['id']
            if id == '36FB82AF-409D-C0ED-4B49-57B1EB08FBD5':
                continue # Null UI Data exists...
            with urllib.request.urlopen(f'{url}{id}') as f:
                data = json.loads(f.read().decode('utf-8'))
            x['abilities'] = data['data']['abilities']

    def initialiseContent(self):
        with open('localValorantContent/content.json', 'r', encoding='utf-8') as f:
            try:
                self.content = json.loads(f.readline())
            except:
                print("Error loading the content. Pull a new copy.")
                return
        self.checkContentForAbilities()

    def initialiseMaps(self):
        mapListUrl = 'https://valorant-api.com/v1/maps'
        localMaps = []
        try:
            with urllib.request.urlopen(mapListUrl) as f:
                remoteMaps = json.loads(f.read().decode('utf-8'))['data']
        except:
            print("Error getting remote maps")
            return
        with open('localValorantContent/maps.json', 'r', encoding='utf-8') as f:
            try:
                localMaps = json.loads(f.readline())        
            except:
                pass
        for x in remoteMaps:
            if x not in localMaps:
                localMaps.append(x)
        with open('localValorantContent/maps.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(localMaps))

    ##########################################

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Valorant(bot))
