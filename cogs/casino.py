import asyncio
import discord
from discord.ext import commands
import motor.motor_asyncio



class Casino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.initialise())

    async def initialise(self):
        mongo = motor.motor_asyncio.AsyncIOMotorClient(str(secret))
        db = mongo.userdata
        cursor = db.koomdata.find({})
        for doc in await cursor.to_list(length=100):
            print(doc)
    
def setup(bot):
    bot.add_cog(Casino(bot))