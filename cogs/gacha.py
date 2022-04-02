from math import ceil
from riotwatcher import LolWatcher, ApiError
from bson.objectid import ObjectId
import secrets, discord, json, re, time
import asyncio
from random import Random
from discord.ext import commands

#Rarities
#Inventory Cap
#Claim cap

class Gacha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.database = self.bot.db.gacha_data
        self.watcher = LolWatcher(secrets.riotKey)
        with open('league_skins_uri.txt') as f:
            self.skinURIs = f.readline().split(',')
        self.skinTiers = self.loadSkinTiers()
        self.ORIGINAL_SPAWN_CHANCE = 0.43
        self.SPAWN_CHANCE = self.ORIGINAL_SPAWN_CHANCE # % chance to spawn per attempt
        self.SPAWN_INCREMENT = 0.065 # % chance increase after each spawn attempt
        self.current_spawn = None
        self.current_spawn_msg = None
        self.current_spawn_embed = None
        # 0 = did , 1 = displayname, 2 = inv, 3 = fav , 4 = page, 5 = msgRef, 6  = channel
        self.activeSkinLists = []
        # 0 = sender_id, 1 = sender_name, 2 = receiver_id, 3 = receiver_name, 4 = sender_offers, 5 = rec_offers, 6 = msg
        self.activeTradeOffers = []
        self.activeTrades = [] # 7 = sender_state, 8 = rec_state
        self.random = Random()
        self.claimed_skins = asyncio.get_event_loop().run_until_complete(self.fetchClaimedList())

    @commands.Cog.listener()
    async def on_ready(self):
        self.channel = self.bot.get_channel(secrets.testGacha)
        self.spawn_task = asyncio.get_event_loop().create_task(self.spawnSkins())

    @commands.Cog.listener()
    async def on_message(self, user_msg):
        for msg in self.activeSkinLists:
            if msg[0] == user_msg.author.id:
                self.activeSkinLists.remove(msg)
                return

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        for msg in self.activeSkinLists:
            if msg[0] == user.id:
                if reaction.emoji == '⬅️':
                    if msg[4] == 0:
                        return
                    msg[4] = msg[4] - 1
                    await self.printSkinPage(msg)
                if reaction.emoji == '➡️':
                    if msg[4] >= len(msg[2])-1:
                        return
                    msg[4] = msg[4] + 1
                    await self.printSkinPage(msg)
        for msg in self.activeTradeOffers:
            if msg[2] == user.id:
                if reaction.emoji == '✅':
                    await msg[6].clear_reactions()
                    await self.buildTradeOffer(msg)
                    await msg[6].add_reaction(emoji='✅')
                    await msg[6].add_reaction(emoji='❌')
                    self.activeTrades.append([msg[0],msg[1],msg[2],msg[3],msg[4],msg[5],msg[6],None,None])
                    self.activeTradeOffers.remove(msg)
                    return
                if reaction.emoji == '❌':
                    await self.sendRejectedOfferMsg(msg)
                    self.activeTradeOffers.remove(msg)
                    return
        for msg in self.activeTrades:
            if msg[0] == user.id:
                if reaction.emoji == '✅':
                    msg[7] = True
                if reaction.emoji == '❌':
                    await self.sendCancelledTradeMsg(msg, 1)
                    self.activeTrades.remove(msg)                 
                    return 
            if msg[2] == user.id:
                if reaction.emoji == '✅':
                    msg[8] = True
                if reaction.emoji == '❌':
                    await self.sendCancelledTradeMsg(msg, 3)
                    self.activeTrades.remove(msg)                 
                    return
            if msg[7] and msg[8]:
                await self.doTrade(msg)
                self.activeTrades.remove(msg)
            return   

    async def doTrade(self, msg):
        sender_id = msg[0]
        receiver_id = msg[2]
        sender_list = msg[4]
        receiver_list = msg[5]
        sent = '\n'.join(sender_list)
        received = '\n'.join(receiver_list)
        if sent == '':
            sent = '\u200b'
        if received == '':
            received = '\u200b' 
        for x in receiver_list:
            self.database.update_one({'_did':sender_id}, {'$push':{'_inventory':x}})
            self.database.update_one({'_did':receiver_id},{'$pull':{'_inventory':x}})
        for x in sender_list:
            self.database.update_one({'_did':receiver_id},{'$push':{'_inventory':x}})
            self.database.update_one({'_did':sender_id},{'$pull':{'_inventory':x}})
        embed = discord.Embed(title="Skin Trade Complete", color=0x2abf2d)
        embed.set_thumbnail(url=f"{secrets.skinBaseURL}lol.png")
        embed.add_field(name=f"{msg[1]} Sent",value=f"{sent}")
        embed.add_field(name="\u200b",value="\u200b")
        embed.add_field(name=f"{msg[3]} Sent",value=f"{received}")
        await msg[6].edit(embed=embed)

    async def sendCancelledTradeMsg(self, msg, cancelee):
        embed = discord.Embed(title="Skin Trade Cancelled", color=0xc91e1e)
        embed.set_thumbnail(url=f"{secrets.skinBaseURL}lol.png")
        embed.add_field(name=f"{msg[cancelee]} cancelled the trade",value="\u200b")
        await msg[6].edit(embed=embed)
        await msg[6].clear_reactions()

    async def sendRejectedOfferMsg(self, msg):
        embed = discord.Embed(title="Skin Trade Rejected", color=0xc91e1e)
        embed.set_thumbnail(url=f"{secrets.skinBaseURL}lol.png")
        embed.add_field(name=f"{msg[3]} rejected the trade",value="\u200b")
        await msg[6].edit(embed=embed)
        await msg[6].clear_reactions()

    @commands.command(aliases=['removetrade','skinremove','traderemove','removeskin', 'removeoffer','deloffer'])
    async def delSkinFromTrade(self, pCtx,index:str):
        discord_id = pCtx.message.author.id
        await self.checkIfUserInDatabase(discord_id)
        try:
            index = int(index)
        except:
            await pCtx.send("Invalid index for skin")
            return
        user = await self.database.find_one({'_did':discord_id})
        inventory = user['_inventory']
        if len(inventory) < index:
            await pCtx.send("You don't have that many skins")
            return
        found = False
        for x in self.activeTrades:
            if x[0] == discord_id:
                found=True
                msg = x
                if (x[4].__contains__(inventory[index-1])):
                    x[4].remove(inventory[index-1])
            elif x[2] == discord_id:
                found=True
                msg = x
                if (x[5].__contains__(inventory[index-1])):
                    x[5].remove(inventory[index-1])
        if not found:
            await pCtx.send("You're not currently in a trade")
            return
        await self.buildTradeOffer(msg)
        
    @commands.command(aliases=['addtrade','tradeadd','tradeofferadd','skintradeadd','addskin','skinadd', 'addoffer'])
    async def addSkinToTrade(self, pCtx, index : str):
        discord_id = pCtx.message.author.id
        await self.checkIfUserInDatabase(discord_id)
        try:
            index = int(index)
        except:
            await pCtx.send("Invalid index for skin.")
            return
        user = await self.database.find_one({'_did':discord_id})
        inventory = user['_inventory']
        if len(inventory) < index:
            await pCtx.send("You don't have that many skins.")
            return
        found = False
        for x in self.activeTrades:
            if x[0] == discord_id:
                x[4].append(inventory[index-1])
                msg = x
                found=True
            elif x[2] == discord_id:
                x[5].append(inventory[index-1])
                msg = x
                found=True
        if not found:
            await pCtx.send("You're not currently in any active trades.")
            return
        await self.buildTradeOffer(msg)

    async def buildTradeOffer(self, msg):
        sender_offers = "\u200b"
        receiver_offers = "\u200b"
        for x in range(0,len(msg[4])):
            sender_offers += f"{x+1}. {msg[4][x]}\n"
        for x in range(0,len(msg[5])):
            receiver_offers += f"{x+1}. {msg[5][x]}\n"

        embed = discord.Embed(title="Skin Trade", color=0x21dbb9)
        embed.set_thumbnail(url=f"{secrets.skinBaseURL}lol.png")
        embed.add_field(name=f"{msg[1]}'s Offering",value=f"{sender_offers}")
        embed.add_field(name="\u200b",value="\u200b")
        embed.add_field(name=f"{msg[3]}'s Offering",value=f"{receiver_offers}")
        await msg[6].edit(embed=embed)

    @commands.command(aliases=['trade','tradeoffer'])
    async def makeTradeOffer(self, pCtx):
        discord_id = pCtx.message.author.id
        await self.checkIfUserInDatabase(discord_id)
        mention = pCtx.message.mentions[0]
        await self.checkIfUserInDatabase(mention.id)
        if mention is None:
            await pCtx.send("You didn't @ anyone to trade with.")
            return
        for x in self.activeTradeOffers:
            if x[0] == mention.id or x[1] == mention.id:
                await pCtx.send("The other person is already in a trade.")
                return
            elif x[0] == discord_id or x[1] == discord_id:
                await pCtx.send("You're already taking part in another trade.")
                return
        embed = discord.Embed(title="Skin Trade Offer", color=0x2ebf87)
        embed.set_thumbnail(url=f"{secrets.skinBaseURL}lol.png")
        embed.add_field(name=f"From {pCtx.message.author.display_name}", value="\u200b",inline=False)
        embed.add_field(name=f"{mention.display_name}",value="Do you accept?", inline=False)
        msg = await pCtx.send(embed=embed)
        await msg.add_reaction(emoji='✅')
        await msg.add_reaction(emoji='❌')
        self.activeTradeOffers.append((discord_id, pCtx.message.author.display_name, mention.id, mention.display_name, [],[],msg))             

    @commands.command(aliases=['slist','skinlist','listskins'])
    async def printSkins(self, pCtx):
        discord_id = pCtx.message.author.id
        await self.checkIfUserInDatabase(discord_id)
        userdata = await self.database.find_one({'_did':discord_id})
        inventory = userdata['_inventory']
        favourite = userdata['_favourite']
        channel = pCtx.message.channel.id
        display_name = pCtx.message.author.display_name
        msgData = (discord_id, display_name, inventory, favourite, 0, None, channel)
        self.activeSkinLists.append(msgData)
        await self.printSkinPage(msgData)

    async def printSkinPage(self, msgData):
        # 0 = did , 1 = displayname, 2 = inv, 3 = fav , 4 = page, 5 = msgRef, 6  = channel
        name = msgData[1]
        inv = msgData[2]
        fav = msgData[3]
        page = msgData[4]
        msg = msgData[5]
        channel = self.bot.get_channel(msgData[6])
        fav_url = self.convertSkinToUrl(fav)
        if fav_url == ".jpg":
            fav_url = "lol.png"
        fav_url = f"{secrets.squareBaseUrl}{fav_url}"
        embed = discord.Embed(title=f"{name}'s Skin List", color=0x357ad4)
        embed_body = ''
        startIndex = page * 10
        endIndex = startIndex + 10
        maxPage = int(ceil(len(inv) / 10))
        for x in range(startIndex,endIndex):
            if len(inv) == x:
                break
            embed_body += f'{x+1}. {inv[x]}\n'
        if embed_body == '':
            embed.add_field(name="No Skins", value="Collect them when they spawn!", inline=False)
        else:
            embed.add_field(name=f'Page {page+1} of {maxPage}', value=embed_body, inline=False)
        embed.set_thumbnail(url=fav_url)
        if msg is None:
            msg = await channel.send(embed=embed)
            if embed_body == '':
                self.activeSkinLists.remove(msgData)
                return
            await msg.add_reaction('⬅️')
            await msg.add_reaction('➡️')    
            msgData[5] = msg        
        else:
            await msg.edit(embed=embed)
            
    @commands.command('claim')
    async def skinClaim(self, pCtx, *input : str):
        await self.checkIfUserInDatabase(pCtx.message.author.id)
        input = ' '.join(input)
        if self.current_spawn == input:
            await self.sendSuccessClaimMessage(pCtx)
            await self.updateUserDatabase(pCtx) #User copy
            await self.addClaimToDB() #Database copy
            self.claimed_skins.push(self.current_spawn) #Local copy
            self.current_spawn = None
        else:
            await self.sendFailedClaimMessage(pCtx)

    async def sendSuccessClaimMessage(self, pCtx):
        await pCtx.message.add_reaction(emoji='😍')
        self.current_spawn_embed.set_footer(text=f"Claimed by: {pCtx.message.author.display_name}")
        await self.current_spawn_msg.edit(embed=self.current_spawn_embed)
        self.current_spawn_embed = None
        self.current_spawn_msg = None
        await pCtx.send(f"Congratulations {pCtx.message.author.display_name}, you claimed **{self.current_spawn}**")

    async def sendFailedClaimMessage(self, pCtx):
        await pCtx.message.add_reaction(emoji='🥺')

    async def spawnSkins(self):
        while True: 
            startTime = time.time()
            endTime = startTime + 100 #Try get a new skin for this amount of time, if can't find one, assume all skins have been collected
            #randNum = self.random.random() * 100
            randNum = 0
            if randNum <= self.SPAWN_CHANCE:
                while True:
                    if time.time() > endTime:
                        self.spawn_task.cancel()
                        print("ALL SKINS COLLECTED")
                        break
                    randSkin = self.convertSkinToUrl(self.getRandomSkin())
                    print(randSkin)
                    if not self.claimed_skins.__contains__(self.convertUrlToSkin(randSkin)):
                        break
                self.SPAWN_CHANCE = self.ORIGINAL_SPAWN_CHANCE
                await self.writeSpawnMessage(randSkin)
            else:
                self.SPAWN_CHANCE += self.SPAWN_INCREMENT
            await asyncio.sleep(self.random.random() + 1) 

    async def writeSpawnMessage(self, skin : str):
        embed = discord.Embed(title="Skin Spawned!", description="Claim using 'bruh claim \_\_\_\_\_'", color=0xebc428)
        url = f"{secrets.skinBaseURL}{skin}"
        embed.set_image(url=url)
        formatted_skin = self.convertUrlToHidden(skin)
        embed.add_field(name=f'{formatted_skin}', value='\u200b')
        self.current_spawn = self.convertUrlToSkin(skin)
        self.current_spawn_embed = embed
        self.current_spawn_msg = await self.channel.send(embed=embed)

    def getRandomSkin(self):
        ticket = self.random.randint(0,46101)
        if ticket <20000:
            print("tier1")
            return self.random.choice(self.skinTiers[0])
        elif ticket < 32000:
            print("tier2")
            return self.random.choice(self.skinTiers[1])
        elif ticket < 40000:
            print("tier3")
            return self.random.choice(self.skinTiers[2])
        elif ticket < 45000:
            print("tier4")
            return self.random.choice(self.skinTiers[3])
        elif ticket < 46000:
            print("tier5")
            return self.random.choice(self.skinTiers[4])
        elif ticket < 46100:
            print("tier6")
            return self.random.choice(self.skinTiers[5])
        print("tier7")
        return self.random.choice(self.skinTiers[6])

    def loadSkinTiers(self):
        with open("gacha_rarities.txt") as f:
            data = f.readline().split(',')
        tier1 = []
        tier2 = []
        tier3 = []
        tier4 = []
        tier5 = []
        tier6 = []
        tier7 = []
        for x in data:
            try:
                cost = int(x.split('+')[1])
                skin = x.split('+')[0]
            except Exception as e:
                continue
            if cost >= 260 and cost <= 500:
                tier1.append(skin)
            elif cost >=520 and cost <= 585:
                tier2.append(skin)
            elif cost >= 750 and cost <= 880:
                tier3.append(skin)
            elif cost == 975:
                tier4.append(skin)
            elif cost >= 1350 and cost <= 2400:
                tier5.append(skin)
            elif cost >= 2775 and cost <= 5000:
                tier6.append(skin)
            else:
                tier7.append(skin)
            
        return [tier1,tier2,tier3,tier4,tier5,tier6,tier7]

    async def fetchClaimedList(self):
        claimedObj = await self.database.find_one({'_id': ObjectId(secrets.gachaID)})
        return claimedObj['claimed']

    @commands.command(aliases=['stop_gacha', 'stopgacha', 'gachastop'])
    async def stopGacha(self, pCtx):
        if pCtx.message.author.id != secrets.keironID:
            return
        self.spawn_task.cancel()

    @commands.command(aliases=['start_gacha', 'startgacha', 'gachastart'])
    async def stopGacha(self, pCtx):
        if pCtx.message.author.id != secrets.keironID:
            return
        self.spawn_task = asyncio.get_event_loop().create_task(self.spawnSkins())

    async def addClaimToDB(self):
        await self.database.update_one({'_id':ObjectId(secrets.gachaID)}, {'$push':{'claimed':self.current_spawn}})

    async def updateUserDatabase(self, pCtx):
        discord_id = pCtx.message.author.id
        await self.database.update_one({'_did':discord_id},{'$push':{'_inventory':self.current_spawn}})

    def convertSkinToUrl(self, skinName):
        return '_'.join(skinName.split(' ')) + '.jpg'

    def convertUrlToSkin(self, url):
        return url.replace('_',' ').replace('.jpg','')

    def convertUrlToHidden(self, url):
        formatted_skin = self.convertUrlToSkin(url)
        formatted_skin = re.sub('[A-Za-z0-9]','\_',formatted_skin)
        return formatted_skin

    async def checkIfUserInDatabase(self, discord_id):
        user = await self.database.find_one({'_did':discord_id})
        if user is None:
            entry = {"_did":discord_id, "_inventory":[], "_wishlist":[], "_favourite":""}
            await self.database.insert_one(entry)


def setup(bot):
    bot.add_cog(Gacha(bot))