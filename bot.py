import discord, secrets, os, motor.motor_asyncio, asyncio, sqlite3
from discord.ext import commands

class KoomBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='bruh ', intents=discord.Intents.all(), application_id=881586576235315220, case_insensitive=True)
        #self.mongo = motor.motor_asyncio.AsyncIOMotorClient(str(secrets.mongoKey))
        #self.db = self.mongo.userdata

    async def on_ready(self):
        print(f"{self.user} has connected to Discord.")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='the drip.'))

    async def close(self):
        await super().close()

    @commands.command()
    async def load(self,ctx, cog):
        if ctx.author.id is not secrets.keironID:
            return
        await self.load_extension(f'cogs.{cog}')
        await ctx.send(f"Loaded {cog}")

    @commands.command()
    async def unload(self, ctx, cog):
        if ctx.author.id is not secrets.keironID:
            return
        await self.unload_extension(f'cogs.{cog}')
        await ctx.send(f"Unloaded {cog}")

    async def setup_hook(self):
        for x in os.listdir('./cogs'):
            if x.endswith('.py'):
                await self.load_extension(f'cogs.{x[:-3]}')
                print(f'Loaded: {x[:-3]}')
        synced = await bot.tree.sync()
        #synced = await bot.tree.sync(guild=discord.Object(817238795966611466))
        #print(synced)

bot = KoomBot()
bot.run(secrets.discordToken)
