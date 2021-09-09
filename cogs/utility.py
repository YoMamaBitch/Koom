import discord
from discord.ext import commands

class Utility(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(status=discord.Status.online, activity=discord.Game('Buying Cock Rings'))
        print(f'{self.bot.user} has connected')
    
def setup(bot):
    bot.add_cog(Utility(bot))