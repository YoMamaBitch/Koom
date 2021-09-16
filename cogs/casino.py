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
        self.lottery.start()

    @commands.Cog.listener()
    async def on_command_error(self, pCtx, error):
        if isinstance(error, commands.CommandOnCooldown):
            msg = '**On Cooldown!** Try again in {:.2f}s'.format(error.retry_after)
            await pCtx.send(msg)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        for game in self.bjSessions:
            await game.update(reaction, user)

    @commands.command(name='ltimer')
    async def lotTimer(self,pCtx):
        try:
            lotObject = await self.bot.db.koomdata.find_one({'_id':ObjectId(secrets.lotteryAmount)})
        except Exception as e:
            print(e)
        endTime = lotObject['_lotteryEndTime']
        timeleft = int(endTime - time.time())
        await pCtx.send(f"Lottery ends in: {timeleft}s")

    @commands.command(aliases=['joinlottery','joinl','lottery'])
    async def joinLot(self, pCtx):
        try:
            player = await self.bot.db.koomdata.find_one({'_uid':pCtx.message.author.id})
        except Exception as e:
            print(e)
        await self.bot.db.koomdata.update_one({'_id':ObjectId('613ce2090e01049878d07fb5')}, {'$addToSet':{'_participants':player['_uid']}})
        await pCtx.send(":white_check_mark: You've been added to the lottery!")

    @tasks.loop(seconds=0.0, minutes=30.0, hours=0, count=None)
    async def lottery(self):
        channel = self.bot.get_channel(secrets.casinoChannel)
        lotteryObject = await self.bot.db.koomdata.find_one({'_id':ObjectId('613ce2090e01049878d07fb5')})
        timelefts = int(lotteryObject['_lotteryEndTime'] - time.time())
        if timelefts > 0:
            embed = discord.Embed(title="Lottery!", 
            description='All money lost to the system is returned here in this lottery, every 3 hours!', 
            color=0xD4ADCF, footer="type 'bruh joinl' to join the lottery!")
            amount = lotteryObject['_lotteryAmount']
            embed.add_field(name='Current Prize', value=f'£{amount}')
            embed.add_field(name='Time Left',value=f'{timelefts}s')
        elif timelefts <= 0:
            if len(lotteryObject['_participants']) == 0:
                embed = discord.Embed(title='Lottery Delayed', color=0xD4ADCF, description='No contestants in prize pool, rolling again in 1 hour')
                await channel.send(embed=embed)
                self.bot.db.koomdata.update_one({'_uid':ObjectId('613ce2090e01049878d07fb5')}, {'$inc':{'_lotteryEndTime':3600}})
                return
            ranIndex = random.randrange(0,len(lotteryObject['_participants']))
            ranWinner = lotteryObject['_participants'][ranIndex]
            embed = discord.Embed(title='Lottery Results!', color=0xD4ADCF)
            lotPrize = lotteryObject['_lotteryAmount']
            embed.add_field(name='Grand Prize', value=f'£{lotPrize}')
            embed.add_field(name='Winner', value=f'<@{ranWinner}>')
            await self.bot.db.koomdata.update_one({'_uid':ranWinner}, {'$inc':{'_currency':lotPrize}})
            await self.bot.db.koomdata.update_one({'_id':ObjectId('613ce2090e01049878d07fb5')}, {'$set':{'_lotteryAmount':0}})
            endtime = time.time() + lotteryObject['_lotteryLength']
            await self.bot.db.koomdata.update_one({'_id':ObjectId('613ce2090e01049878d07fb5')}, {'$set':{'_lotteryEndTime':endtime}})
            await self.bot.db.koomdata.update_one({'_id':ObjectId('613ce2090e01049878d07fb5')}, {'$set':{'_participants':[]}})
        await channel.send(embed=embed)

    @lottery.before_loop
    async def lottery_before(self):
        await self.bot.wait_until_ready()

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