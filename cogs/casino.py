import asyncio
from coinflip import Coinflip
import blackjack
import hangman
from dice import Dice
import discord
from discord import user
from discord.ext import commands
import motor.motor_asyncio
import random
import secrets
import time
from bson.objectid import ObjectId

class Casino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bjSessions = []
        self.hmSessions = []
        
    @commands.Cog.listener()
    async def on_command_error(self, pCtx, error):
        if isinstance(error, commands.CommandOnCooldown):
            msg = '**On Cooldown!** Try again in {:.2f}s'.format(error.retry_after)
            await pCtx.send(msg)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        for game in self.bjSessions:
            await game.update(reaction, user)

    @commands.command(aiases=['config dice','diceconfig'])
    async def dic(self,pCtx):
        game = Dice(self.bot, pCtx.message)
        await game.displayConfig()

    @commands.command(aliases=['configroll','rollconfig'])
    async def dir(self,pCtx, roll):
        game = Dice(self.bot, pCtx.message)
        await game.updateConfigRoll(roll)

    @commands.command(aliases=['configpayout','payoutconfig'])
    async def dip(self,pCtx,payout):
        game = Dice(self.bot, pCtx.message)
        await game.updateConfigPayout(payout)

    @commands.command(aliases=['rolldice', 'diceroll'])
    async def di(self, pCtx, amount : int):
        game = Dice(self.bot, pCtx.message, amount)
        await game.start()

    @commands.command(name='coinflip')
    async def cf(self, pCtx, amount : int, guess, otherPlayer = None):
        game = Coinflip(self.bot, pCtx.message, guess, amount, otherPlayer)
        await game.start()

    @commands.command(name='hangman')
    async def hm(self,pCtx,amount:int):
        if amount < 0:
            await pCtx.send("Can't bet a negative amount")
            return
        ID = pCtx.message.author.id
        #for game in self.hmSessions:
        #    if game.player == ID:
        #        await pCtx.send("You're already in a hangman game")
        #        return
        user = await self.bot.db.koomdata.find_one({'_uid':int(ID)})
        if user['_currency'] < amount:
            await pCtx.send("Not enough money to gamble")
            return
        try:
            game = hangman.HangmanGame(self.bot, pCtx.message, amount, self.hmSessions)
        except Exception as e:
            print(e)
        self.hmSessions.append(game)
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