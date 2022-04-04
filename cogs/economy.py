import discord, secrets
from discord import app_commands
from discord.ext import commands

class Economy(commands.Cog):
    def __init__(self,bot:commands.Bot)->None:
        self.bot = bot
    
    @app_commands.command(name="pay",description="Pay someone")
    async def pay(self,interaction:discord.Interaction,user:discord.User,amount:float)->None:
        await interaction.response.send_message(f"You have paid £{amount} to {user.display_name}")

    async def dbSendMoneyTo(self, user : discord.User, amount : float):
        await self.database.update_one({'_did':user.id}, {'$inc':{'_currency':amount}})

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Economy(bot), guild=secrets.testGuild)