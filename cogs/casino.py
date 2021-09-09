import asyncio
import discord
from discord.ext import commands
import motor.motor_asyncio



class Casino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = []
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.initialise())

    async def initialise(self):
        self.bot.mongo = motor.motor_asyncio.AsyncIOMotorClient(str(secret))
        self.bot.db = self.bot.mongo.userdata
        await self.load_data()
    
    async def load_data(self):
        self.bot.cursor = self.bot.db.koomdata.find({})
        docs = await self.bot.cursor.to_list(length=1000)
        await self.update_players(docs)
    
    async def update_players(self, docs):
        test = 0

def setup(bot):
    bot.add_cog(Casino(bot))

class Userdata():
    def __init__(self, author, currency):
        self.author = author
        self.currency = currency