from riotwatcher import LolWatcher, ApiError
from bson.objectid import ObjectId
import secrets, discord, json, re
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
        self.ORIGINAL_SPAWN_WEIGHT = 0.45
        self.SPAWN_WEIGHT = self.ORIGINAL_SPAWN_WEIGHT # % chance to spawn per attempt
        self.SPAWN_INCREMENT = 0.1 # % chance increase after each spawn attempt
        self.current_spawn = None
        self.current_spawn_hidden = None
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

    async def spawnSkins(self):
        while True:
            while True:
                randSkin = self.random.choice(self.skinURIs)
                if not self.claimed_skins.__contains__(randSkin):
                    break
            await self.writeSpawnMessage(randSkin)
            await asyncio.sleep(self.random.random() + 10)

    async def writeSpawnMessage(self, skin : str):
        embed = discord.Embed(title="Skin Spawned!", description="Claim using 'bruh claim \_\_\_\_\_'", color=0xebc428)
        url = f"{secrets.skinBaseURL}{skin}"
        embed.set_image(url=url)
        formatted_skin = skin.replace('_',' ').replace('.jpg','')
        formatted_skin = re.sub('[A-z]','\_',formatted_skin)
        embed.add_field(name=f'{formatted_skin}', value='\u200b')
        await self.channel.send(embed=embed)


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
        
   # def pickRandomSpawn():
        


def setup(bot):
    bot.add_cog(Gacha(bot))