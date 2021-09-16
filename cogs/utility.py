import discord
from discord.ext import commands
import random
import asyncio

class Utility(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(status=discord.Status.online, activity=discord.Game('Buying Cock Rings'))
        print(f'{self.bot.user} has connected')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content == "bruh give me info on ronald's rank":
            await message.channel.send("Roger that captain: According to this Riot API...")
            await asyncio.sleep(6)
            await message.channel.send("He's **fucking shit**")

    async def createErrorEmbed(self, description):
        return discord.Embed(title='Error', color=0xC5283D,description=description)

    def removeMentionMarkup(self, mention):
        if '!' in mention:
            response = mention[3:len(mention)-1]
        else:
            response =mention[2:len(mention)-1]
        return response

    async def fetchFromMention(self, mention):
        return await self.bot.fetch_user(self.removeMentionMarkup(mention))
    
def setup(bot):
    bot.add_cog(Utility(bot))