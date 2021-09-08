import discord
from discord.ext import commands
import os

bot = commands.Bot(command_prefix='bruh ')
bot.remove_command('help')
TOKEN = 'ODgxNTg2NTc2MjM1MzE1MjIw.YSu_eg.IGtIlNR-8K9F_iznRZn22Xz-D2Q'

@bot.command()
async def load(ctx,extension):
    bot.load_extension(f'cogs.{extension}')

@bot.command()
async def unload(ctx,extension):
    bot.unload_extension(f'cogs.{extension}')

for file in os.listdir('./cogs'):
    if file.endswith('.py'):
        bot.load_extension(f'cogs.{file[:-3]}')

bot.run(TOKEN)