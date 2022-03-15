import json, requests, discord, os, hashlib, asyncio, secrets, urllib.request, datetime
from discord.ext import commands
from riotwatcher import ValWatcher
from PIL import Image

class Valorant(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.database = self.bot.db.valorant_data
        self.watcher = ValWatcher(secrets.valKey)
        self.active_messages = []
        self.active_matches = []
        self.initialiseMaps()
        self.initialiseContent()

    @commands.Cog.listener()
    async def on_message(self, user_msg):
        for match in self.active_matches:
            if match[0] == user_msg.author.id:
                self.active_matches.remove(match)
                break
        for msg in self.active_messages:
            if msg[0] == user_msg.author.id:
                try:
                    user_choice = int(user_msg.content)
                except Exception as e:
                    self.active_messages.remove(msg)
                    return
            #schema: AuthorID, Match_Data, Overview? (Whether to display image), Round to display (0 = Overview), discord_msg, player_puuid
            self.active_matches.append((user_msg.author.id, msg[2][user_choice-1], True, 0, msg[1], msg[3]))
            self.active_messages.remove(msg)
            await self.editMessage(self.active_matches[len(self.active_matches)-1])
            await msg[1].add_reaction('⏺️')
            await msg[1].add_reaction('⬅️')
            await msg[1].add_reaction('➡️')
            return

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        for msg in self.active_matches:
            if msg[0] == user.id:
                new_msg = await self.parse_emoji(reaction, msg)
                self.active_matches.remove(msg)
                self.active_matches.append(new_msg)

    async def displayOverview(self, match_data, player_puuid, discord_msg):
        player_data = self.getPlayerDataFromMatch(match_data, player_puuid)
        player_stats = player_data['stats']
        player_won = self.getPlayerWinFromMatch(match_data,player_data)
        if player_won:
            color = 0x2bbd59
        else:
            color = 0xab281a
        agent_name = self.getCharacterFromID(player_data['characterId'])
        embed = discord.Embed(title=f"{player_data['gameName']} - {agent_name}",color=color)
        map = self.getMapFromID(match_data['matchInfo']['mapId'])
        length = datetime.datetime.fromtimestamp(match_data['matchInfo']['gameLengthMillis']/1000.0).strftime('%M:%S')
        queue = match_data['matchInfo']['queueId'].capitalize()
        embed.set_author(name=f'{map} - {length} - {queue}')
        gamemode_url = self.getGamemodeImageUrlFromId(match_data['matchInfo']['queueId'])
        embed.set_thumbnail(url=f'{gamemode_url}')
        match_score = self.getMatchScore(match_data,player_data)
        embed.set_footer(text=f'Final Score: {match_score}')
        kills = player_stats['kills']
        deaths = player_stats['deaths']
        assists = player_stats['assists']
        embed.add_field(name='Kills',value=f'{kills}')
        embed.add_field(name='Deaths',value=f'{deaths}')
        embed.add_field(name='Assists',value=f'{assists}')
        grenade_stats = self.getAbilityStats(player_data, "Grenade")
        ability1_stats = self.getAbilityStats(player_data, "Ability1")
        ability2_stats = self.getAbilityStats(player_data, "Ability2")
        ult_stats = self.getAbilityStats(player_data, "Ultimate")
        embed.add_field(name=f'{grenade_stats[0]}', value=f'{grenade_stats[1]}')
        embed.add_field(name=f'{ability1_stats[0]}', value=f'{ability1_stats[1]}')
        embed.add_field(name=f'{ability2_stats[0]}', value=f'{ability2_stats[1]}')
        embed.add_field(name='\u200b', value='\u200b')
        embed.add_field(name=f'{ult_stats[0]}', value=f'{ult_stats[1]}')
        embed.add_field(name='\u200b', value='\u200b')

        characters = self.getCharacterListFromMatch(match_data, player_puuid)
        imagePath = self.compositeMatchImage(characters,match_data['matchInfo']['mapId']) 
        file = discord.File(imagePath, filename="image.png")
        vKChannel = self.bot.get_channel(886389462769217536)
        img_msg = await vKChannel.send(file=file)
        img_url = img_msg.attachments[0].url
        embed.set_image(url=img_url)
        await discord_msg.edit(embed=embed)
        os.remove(imagePath)

    async def displayRound(self, match_data, player_puuid, round, discord_msg):
        round_data = match_data['roundResults'][round-1]
        player_team = self.getPlayerTeamFromMatch(match_data, player_puuid)
        playerWon = round_data['winningTeam'] == player_team
        if playerWon:
            color = 0x2bbd59
        else:
            color = 0xab281a
        round_result = round_data['roundResult'].title()
        embed = discord.Embed(title=f'Result: {round_result}', color=color)
        embed.set_author(name=f'Round: {round}')
        self.setEmbedFooterForRound(embed, round_data)
        player_round_data = self.getPlayerRoundData(round_data, player_puuid)
        kills = self.getPlayerRoundKills(player_round_data['kills'])
        damage = self.getPlayerRoundDamage(player_round_data['damage'])
        eco = player_round_data['economy']['remaining']
        embed.add_field(name='Kills',value=f'{kills}')
        embed.add_field(name='Dmg',value=f'{damage}')
        embed.add_field(name='Eco',value=f'${eco}')
        await discord_msg.edit(embed=embed)

    def getPlayerRoundKills(self, kills):
        return len(kills)

    def getPlayerRoundDamage(self, round_damage):
        sum = 0
        for x in round_damage:
            sum = sum + x['damage']
        return sum

    def setEmbedFooterForRound(self, embed, round_data):
        ceremony = round_data['roundCeremony']
        if ceremony == 'CeremonyDefault':
            return

    def getPlayerRoundData(self, round_data, player_puuid):
        for x in round_data['playerStats']:
            if x['puuid'] == player_puuid:
                return x

    def getPlayerTeamFromMatch(self, match_data, player_puuid):
        for x in match_data['players']:
            if x ['puuid'] == player_puuid:
                player_team = x['teamId']
                return player_team

    def compositeMatchImage(self, characters, mapId):
        map_id = self.getMapIdFromAssetPath(mapId)
        b_img = Image.open(f'cogs/val_character_images/{map_id}.png')
        xPos = -70
        yPos = 150
        for x in characters[0]:
            char_img = Image.open(f'cogs/val_character_images/{x}.png')
            char_img.thumbnail((256,256), Image.ANTIALIAS)
            b_img.paste(char_img, (xPos,yPos), char_img)
            xPos += 115
        xPos += 150
        for x in characters[1]:
            char_img = Image.open(f'cogs/val_character_images/{x}.png')
            char_img.thumbnail((256,256), Image.ANTIALIAS)
            b_img.paste(char_img, (xPos,yPos), char_img)
            xPos += 115
        filePath = f"cogs/{datetime.datetime.now().strftime('%H-%M-%S')}.png"
        b_img.save(filePath)
        return filePath

    def getAbilityStats(self, player_data, ability):
        characters = self.content['characters']
        player_stats = player_data['stats']
        for x in characters:
            if x['id'] == player_data['characterId'].upper():
                character_to_get = x
        ability_name = character_to_get['abilities'][f'{ability}']['name']['defaultText']
        ability_name = ability_name.title()
        ability_casts = ability.lower() + "Casts"
        player_uses = player_stats['abilityCasts'][f'{ability_casts}']
        return (ability_name, player_uses)

    def getMatchScore(self, match_data, player_data):
        for x in match_data['teams']:
            if x['teamId'] == 'Blue':
                blue_score = x['roundsWon']
            else:
                red_score = x['roundsWon']
        if player_data['teamId'] == 'Blue':
            return f"{blue_score}-{red_score}"
        else:
            return f"{red_score}-{blue_score}"

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
        icon_url = f"https://thebestcomputerscientist.co.uk/valorant_content/playercards/{icon_url}.png"
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
        msg = await pCtx.send(embed=embed)
        self.active_messages.append((pCtx.message.author.id, msg, matches, player_puuid))

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

    def initialiseMaps(self):
        map_names = []
        url = requests.get('https://valorant-api.com/v1/maps')
        text = url.text
        json_data = json.loads(text)
        for x in json_data['data']:
            map_names.append(x['uuid'])
        for filename in os.listdir('cogs/val_map_data'):
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
                with open(f'cogs/val_map_data\\{x}map.jpg', 'wb') as f:
                    f.write(url.read())

    def initialiseContent(self):
        #try:
        #    content_data = self.watcher.content.contents('EU', 'en-GB')
        #except Exception as e:
        #    print(e)
        #    return
        #version = '0'
        try:
            with open('cogs/val_content_en_gb.json', encoding='utf8') as json_file:
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
                return x['name']['defaultText']
        
    def getMapFromID(self, id):
        maps = self.content['maps']
        for x in maps:
            if 'assetPath' not in x:
                continue
            if x['assetPath'] == id:
                return x['name']['defaultText']

    def getMatchFromID(self, matchID):
        return self.watcher.match.by_id('EU',matchID)

    def getGamemodeImageUrlFromId(self, modeId):
        gameModes = self.content['gameModes']
        for x in gameModes:
            if x['name']['defaultText'] == modeId:
                id = x['id']
                return f"https://thebestcomputerscientist.co.uk/valorant_content/gamemodes/{id}.png"
    
    def getMapImageUrlFromID(self, mapId):
        maps = self.content['maps']
        for x in maps:
            if 'assetPath' not in x:
                continue
            if x['assetPath'] == mapId:
                id = x['id']
                return f"https://thebestcomputerscientist.co.uk/valorant_content/maps/{id}.png"
    
    def getMapIdFromAssetPath(self, mapAsset):
        maps = self.content['maps']
        for x in maps:
            if 'assetPath' not in x:
                continue
            if x['assetPath'] == mapAsset:
                return x['id']

    def getPlayerDataFromMatch(self, match_data, player_puuid):
        for x in match_data['players']:
            if x['puuid'] == player_puuid:
                return x

    def getPlayerWinFromMatch(self, match_data, player_data):
        player_team = player_data['teamId']
        for x in match_data['teams']:
            if x['teamId'] == player_team:
                return x['won']

    def getPlayerTitleFromMatch(self, puuid, match):
        title_id = self.getPlayerDataFromMatch(match,puuid)['playerTitle'].upper()
        titles = self.content['playerTitles']
        for x in titles:
            if 'id' not in x:
                continue
            if x['id'] == title_id:
                return x['titleText']['defaultText'].replace('Title','')

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

    def getCharacterListFromMatch(self, match_data, player_puuid):
        red_players = []
        blue_players = []
        for x in match_data['players']:
            if x['puuid'] == player_puuid:
                player_team = x['teamId']
            if x['teamId'] == 'Blue':
                blue_players.append(x['characterId'].upper())
            else:
                red_players.append(x['characterId'].upper())
        if player_team == 'Red':
            return (red_players,blue_players)
        return (blue_players, red_players)

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

    async def parse_emoji(self, reaction,match_tuple):
        match_lower = 0
        match_higher = match_tuple[1]['teams'][0]['roundsPlayed']
        match_list = list(match_tuple)
        if reaction.emoji == '⏺️':
            match_list[2] = not match_list[2]
        elif reaction.emoji == '⬅️':
            match_list[2] = False
            if match_list[3] > match_lower:
                match_list[3] = match_list[3] - 1
        elif reaction.emoji == '➡️':
            match_list[2] = False
            if match_list[3] < match_higher:
                match_list[3] = match_list[3] + 1
        match_tuple = tuple(match_list)
        await self.editMessage(match_tuple)
        return match_tuple

    async def editMessage(self, match_tuple):
        if match_tuple[2]:
            await self.displayOverview(match_tuple[1], match_tuple[5], match_tuple[4])
            return
        await self.displayRound(match_tuple[1], match_tuple[5], match_tuple[3], match_tuple[4])
    
    @commands.command(name='authenticate')
    async def authenticateRSO(self,pCtx):
        discord_id = pCtx.message.author.id
        hashed_id = self.getHash(discord_id)
        hashed_id = hashed_id.replace(' ','%20').replace('\\','%5C').replace("'",'%27')
        url = f"https://thebestcomputerscientist.co.uk/html/koom-authenticate.html?id={hashed_id}"
        user = self.bot.get_user(discord_id)
        await user.send(f"Click the following link: {url}\n\nDo not share this link with anyone")


def setup(bot):
    bot.add_cog(Valorant(bot))
