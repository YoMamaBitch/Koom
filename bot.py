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
    await ctx.send(f"Loaded {extension}")
    bot.load_extension(f'cogs.{extension}')

@bot.command()
async def unload(ctx,extension):
    await ctx.send(f"Unloaded {extension}")
    bot.unload_extension(f'cogs.{extension}')

for file in os.listdir('./cogs'):
    if file.endswith('.py'):
        bot.load_extension(f'cogs.{file[:-3]}')
        print('Loaded: %s' %f'cogs.{file[:-3]}')

@bot.command()
async def help(pCtx):
    embed = discord.Embed(title="Need Help with Koom?", color=0xe0e0e0)
    with open('helpText.txt') as file:
        for line in file:
            cmd = line.split('--')[0]
            if (cmd == '\n'):
                cmd = '\u200b'
            try:
                explanation = line.split('--')[1]
            except:
                explanation = '\u200b'
            embed.add_field(name=cmd,value=explanation,inline=False)

    await pCtx.send(embed=embed)


bot.run(secrets.discordKey)