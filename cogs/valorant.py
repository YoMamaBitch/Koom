import json, requests, discord, os, hashlib, asyncio, secrets, urllib.request
from discord.ext import commands
from riotwatcher import ValWatcher
from PIL import Image

class Valorant(commands.Cog):

    def initialiseMaps(self):
        map_names = []
        url = requests.get('https://valorant-api.com/v1/maps')
        text = url.text
        json_data = json.loads(text)
        for x in json_data['data']:
            map_names.append(x['uuid'])
        for filename in os.listdir('cogs\\val_map_data'):
            if map_names.__contains__(filename):
                map_names.remove(filename)
        for x in map_names:
            url = requests.get(f'https://valorant-api.com/v1/maps/{x}')
            json_data = json.loads(url.text)['data']
            img_url = json_data['displayIcon']
            f = open(f'cogs\\val_map_data\\{x}', 'w')
            xMult = json_data['xMultiplier']
            yMult = json_data['yMultiplier']
            xScalarAdd = json_data['xScalarToAdd']
            yScalarAdd = json_data['yScalarToAdd']
            f.write('{' + f'xMultiplier:{xMult},yMultiplier:{yMult},xScalarAdd:{xScalarAdd},yScalarAdd:{yScalarAdd}' + '}')
            f.close()
            if img_url is None:
                continue
            with urllib.request.urlopen(img_url) as url:
                with open(f'cogs\\val_map_data\\{x}map.jpg', 'wb') as f:
                    f.write(url.read())

    def initialiseContent(self):
        #try:
        #    content_data = self.watcher.content.contents('EU', 'en-GB')
        #except Exception as e:
        #    print(e)
        #    return
        #version = '0'
        try:
            with open('cogs\\val_content_en_gb', encoding='utf8') as json_file:
                data = json.load(json_file)
                self.content = data
                #version = data['version']
            #if content_data['version'] != version:
            #    with open('cogs\\val_content_en_gb', 'w', encoding='utf8') as json_file:
            #        json_file.write(json.dumps(content_data))
        except Exception as e:
            print(e)

    def getCharacterFromID(self, id):
        characters = self.content['characters']
        for x in characters:
            if 'id' not in x:
                continue
            if x['id'] == id.upper():
                return x['name']
        
    def getMapFromID(self, id):
        maps = self.content['maps']
        for x in maps:
            if 'assetPath' not in x:
                continue
            if x['assetPath'] == id:
                return x['name']

    def getMatchFromID(self, matchID):
        return self.watcher.match.by_id('EU',matchID)

    def getPlayerDataFromMatch(self, match_data, player_puuid):
        for x in match_data['players']:
            if x['puuid'] == player_puuid:
                return x

    def getPlayerTitleFromMatch(self, puuid, match):
        title_id = self.getPlayerDataFromMatch(match,puuid)['playerTitle'].upper()
        titles = self.content['playerTitles']
        for x in titles:
            if 'id' not in x:
                continue
            if x['id'] == title_id:
                return x['name'].replace('Title','')

    def getPlayerIconFromMatch(self, puuid, match):
        return self.getPlayerDataFromMatch(match, puuid)['playerCard'].upper()

    async def getPlayerMatchHistory(self, discord_id):
        user_data = await self.database.find_one({'_did':discord_id})
        player_puuid = user_data['_puuid']
        match_history = self.watcher.match.matchlist_by_puuid('EU',player_puuid)['history']
        return match_history

    async def checkForMention(self, pCtx):
        if pCtx.message.mentions is None:
            await pCtx.send("Improper use. Mention (@) the user you want.")
            return False
        return True

    def __init__(self, bot):
        self.bot = bot
        self.database = self.bot.db.valorant_data
        self.watcher = ValWatcher(secrets.valKey)
        self.initialiseMaps()
        self.initialiseContent()
        
    def getHash(self, data):
        hasher = hashlib.sha256()
        data_bytes = bytes(str(data), 'utf-8')
        hasher.update(data_bytes)
        hashed_id = hasher.digest()
        hashed_id = str(hashed_id)
        return hashed_id

    async def checkAuthenticated(self, pCtx, userID):
        hashed_id = self.getHash(userID)
        userData = await self.database.find_one({'_uid':hashed_id})
        if userData is None:
            await self.database.insert_one({'_uid':hashed_id,'_did':userID, '_authenticated':False, '_puuid':''})
            userData = await self.database.find_one({'_uid':hashed_id})

        if userData['_authenticated'] == False:
            await pCtx.send("The user is currently not authenticated.")
            await pCtx.send("They need to type 'bruh authenticate'")
            return False        
        return True
    
    @commands.command(name='authenticate')
    async def authenticateRSO(self,pCtx):
        discord_id = pCtx.message.author.id
        hashed_id = self.getHash(discord_id)
        hashed_id = hashed_id.replace(' ','%20').replace('\\','%5C').replace("'",'%27')
        url = f"https://thebestcomputerscientist.co.uk/html/koom-authenticate.html?id={hashed_id}"
        user = self.bot.get_user(discord_id)
        await user.send(f"Click the following link: {url}\n\nDo not share this link with anyone")

    @commands.command(aliases=['val_browse', 'valbrowse','val_list','vallist'])
    async def listmatches(self, pCtx):
        if not await self.checkForMention(pCtx):
            return
        discord_id = pCtx.message.mentions[0].id
        if not await self.checkAuthenticated(pCtx,discord_id):
            return
        match_history = await self.getPlayerMatchHistory(discord_id)
        hashed_id = self.getHash(discord_id)
        player_data = await self.database.find_one({'_uid':hashed_id})
        player_puuid = player_data['_puuid']
        matches = []
        for x in range(0,10):
            matches.append(self.getMatchFromID(match_history[x]['matchId']))
        icon_url = self.getPlayerIconFromMatch(player_puuid,matches[0])
        icon_url = f"https://thebestcomputerscientist.co.uk/playercards/{icon_url}.png"
        player_title = self.getPlayerTitleFromMatch(player_puuid, matches[0])
        embed = discord.Embed(title=f"Match History", color=0x32a8a0)
        embed.set_author(name=f"{pCtx.message.mentions[0].display_name}")
        embed.set_thumbnail(url=icon_url)
        embed.set_footer(text=f'{player_title}')
        descriptionText = ""
        for x in range(0,10):
            descriptionText += f'{x+1}. '
            player_match_data = self.getPlayerDataFromMatch(matches[x],player_puuid)
            character_name = self.getCharacterFromID(player_match_data['characterId'])
            map_name = self.getMapFromID(matches[x]['matchInfo']['mapId'])
            descriptionText += f'{character_name} - {map_name}\n'
        embed.add_field(name='\u200b',value=f'{descriptionText}', inline=False)

        await pCtx.send(embed=embed)


    @commands.command(aliases=['val_recentmatch'])
    async def findonematch(self,pCtx):
        if not await self.checkForMention(pCtx):
            return
        discord_id = pCtx.message.mentions[0].id
        if not await self.checkAuthenticated(pCtx, discord_id):
            return

        match_history = await self.getPlayerMatchHistory(discord_id)
        for x in match_history:
            if x['queueId'] != 'unrated':
                continue
            match_index = x
            break
        match_data = self.watcher.match.by_id('EU',match_index['matchId'])
        #player_data = self.findPlayerDataFromMatch(match_data, player_puuid)


def setup(bot):
    bot.add_cog(Valorant(bot))
