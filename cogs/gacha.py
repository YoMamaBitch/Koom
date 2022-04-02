from riotwatcher import LolWatcher, ApiError
from bson.objectid import ObjectId
import secrets, discord, json, re, time
import asyncio
from random import Random
from discord.ext import commands


class Gacha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.database = self.bot.db.gacha_data
        self.watcher = LolWatcher(secrets.riotKey)
        with open('league_skins_uri.txt') as f:
            self.skinURIs = f.readline().split(',')
        self.ORIGINAL_SPAWN_CHANCE = 0.45
        self.SPAWN_CHANCE = self.ORIGINAL_SPAWN_CHANCE # % chance to spawn per attempt
        self.SPAWN_INCREMENT = 0.1 # % chance increase after each spawn attempt
        self.current_spawn = None
        self.current_spawn_msg = None
        self.current_spawn_embed = None
        self.random = Random()
        self.claimed_skins = asyncio.get_event_loop().run_until_complete(self.fetchClaimedList())

    @commands.Cog.listener()
    async def on_ready(self):
        self.channel = self.bot.get_channel(secrets.testGacha)
        self.spawn_task = asyncio.get_event_loop().create_task(self.spawnSkins())

    async def fetchClaimedList(self):
        claimedObj = await self.database.find_one({'_id': ObjectId(secrets.gachaID)})
        test = claimedObj['claimed']
        return claimedObj['claimed']

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
            randNum = self.random.random() * 100
            if randNum <= self.SPAWN_CHANCE:
                while True:
                    if time.time() > endTime:
                        self.spawn_task.cancel()
                        print("ALL SKINS COLLECTED")
                        break
                    randSkin = self.random.choice(self.skinURIs)
                    if not self.claimed_skins.__contains__(self.convertUrlToSkin(randSkin)):
                        break
                self.SPAWN_CHANCE = self.ORIGINAL_SPAWN_CHANCE
                await self.writeSpawnMessage(randSkin)
            else:
                self.SPAWN_CHANCE += self.SPAWN_INCREMENT
            await asyncio.sleep(self.random.random() * 40 + 20) 

    async def writeSpawnMessage(self, skin : str):
        embed = discord.Embed(title="Skin Spawned!", description="Claim using 'bruh claim \_\_\_\_\_'", color=0xebc428)
        url = f"{secrets.skinBaseURL}{skin}"
        embed.set_image(url=url)
        formatted_skin = self.convertUrlToHidden(skin)
        embed.add_field(name=f'{formatted_skin}', value='\u200b')
        self.current_spawn = self.convertUrlToSkin(skin)
        self.current_spawn_embed = embed
        self.current_spawn_msg = await self.channel.send(embed=embed)

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