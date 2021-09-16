import asyncio
from coinflip import Coinflip
import discord
from discord import user
from discord.ext import commands
import motor.motor_asyncio
import random
import secrets
import time
from bson.objectid import ObjectId
import blackjack

class Casino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bjSessions = []
        
    @commands.Cog.listener()
    async def on_command_error(self, pCtx, error):
        if isinstance(error, commands.CommandOnCooldown):
            msg = '**On Cooldown!** Try again in {:.2f}s'.format(error.retry_after)
            await pCtx.send(msg)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        for game in self.bjSessions:
            await game.update(reaction, user)

    @commands.command(name='coinflip')
    async def cf(self, pCtx, amount : int, guess, otherPlayer = None):
        game = Coinflip(self.bot, pCtx.message, guess, amount, otherPlayer)
        await game.start()

    @commands.command(name='blackjack')
    async def bj(self, pCtx, amount:int):
        if amount < 0:
            await pCtx.send("Can't bet a negative amount")
            return
        ID = pCtx.message.author.id
        for game in self.bjSessions:
            if game.player == ID:
                await pCtx.send("CAN'T START ANOTHER ONE FUCKERR")
                return
        user = await self.bot.db.koomdata.find_one({'_uid':int(ID)})
        if user['_currency'] < amount:
            await pCtx.send("You don't have enough money to gamble")
            return
        try:
            game = blackjack.BlackjackGame(self.bot, pCtx.message, amount, self.bjSessions)
        except Exception as e:
            print(e)
        self.bjSessions.append(game)
        await game.start()

def setup(bot):
    bot.add_cog(Casino(bot))