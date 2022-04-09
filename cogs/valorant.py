import json
import discord,secrets, utility, urllib.request, urllib.parse, hashlib
from riotwatcher import ValWatcher, RiotWatcher
from discord.ext import commands
from discord import app_commands
from valorant_view import ValorantMatchView

class Valorant(commands.Cog):
    def __init__(self,bot:commands.Bot)->None:
        self.bot = bot 
        self.riotwatcher = RiotWatcher(secrets.valKey)
        self.watcher = ValWatcher(secrets.valKey)
        self.playerCardUrl = 'https://media.valorant-api.com/playercards/'
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
        embed_data = [id,0,4,matches,matchlist,puuid,author_name, player_card]
        view = ValorantMatchView(embed_data, self)
        embed_data.append(view)
        embed = self.generateMatchOverview(embed_data)
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
        #0 = did, 1 = start, 2=end,3=matches,4=matchlist,5=puuid,6=author_name,7=playercard,8=view
        #Blue always defend first
        gamename = self.getUserName(embed_data[5])
        playercardUrl = self.playerCardUrl + embed_data[7] + '/smallart.png'
        embed = discord.Embed(title=f'Recent Matches',color=0x1aba9f)
        playerRank = self.getPlayerRankFromMatch(embed_data[3][0],embed_data[5])
        embed.set_author(name=f"{gamename} : {playerRank}")
        embed.set_thumbnail(url=playercardUrl)
        playerTitle = self.getPlayerTitleFromMatch(embed_data[3][0], embed_data[5])
        embed.set_footer(text=playerTitle)
        while len(embed_data[3]) < embed_data[2]+1:
            matchId = embed_data[4][len(embed_data[3])]
            embed_data[3].append(self.watcher.match.by_id('EU',matchId['matchId']))         
        fieldDesc = ''
        for i in range(embed_data[1], embed_data[2]+1):
            agent = self.getAgentFromMatch(embed_data[3][i], embed_data[5])
            mapName = self.getMapNameFromMatch(embed_data[3][i])
            gameLengthStr = self.getMatchLength(embed_data[3][i])
            kills = self.getPlayerKillsFromMatch(embed_data[3][i], embed_data[5])
            fieldDesc += f'```yaml\n{agent} : {mapName} : {gameLengthStr} : {kills} Kills\n```'
            #embed.add_field(name=f'Match {i+1}', value=fieldDesc,inline=False)
        embed.add_field(name='\u200b', value=fieldDesc, inline=False)
        return embed

    def getMatchLength(self, match):
        lengthMs = match['matchInfo']['gameLengthMillis']
        return utility.secondsToMinSecString(int(lengthMs / 1000))

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
        #Do something here 

    def isPlayerAttackOrDefend(self, match, puuid, round):
        team = self.getPlayerTeamFromMatch(match,puuid)
        if (team == 'Blue' and round < 12) or (team=='Red' and round >= 12):
            return 'Defense'
        return 'Attack'

    def getPlayerTeamFromMatch(self, match,puuid):
        return self.getPlayerDataFromMatch(match,puuid)['teamId']

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
