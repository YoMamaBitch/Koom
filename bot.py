import discord
from discord.ext import commands
import motor.motor_asyncio
import os
import secrets

bot = commands.Bot(command_prefix='bruh ', intents=discord.Intents().all(), case_insensitive=True)
bot.remove_command('help')
bot.mongo = motor.motor_asyncio.AsyncIOMotorClient(str(secrets.mongoKey))
bot.db = bot.mongo.userdata
@bot.command()
async def load(ctx,extension):
    bot.load_extension(f'cogs.{extension}')

@bot.command()
async def unload(ctx,extension):
    bot.unload_extension(f'cogs.{extension}')

for file in os.listdir('./cogs'):
    if file.endswith('.py'):
        bot.load_extension(f'cogs.{file[:-3]}')
        print('Loaded: %s' %f'cogs.{file[:-3]}')

bot.run(secrets.discordKey)