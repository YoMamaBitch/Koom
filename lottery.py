import discord
from discord.ext import commands
from discord.ext import tasks
import asyncio
import random
import secrets
from bson.objectid import ObjectId
import time

from discord.ext.commands.core import command

class Lottery(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.database = self.bot.db.koomdata
        #self.lottery.start()
    
    @commands.command(name='ltimer')
    async def lotteryTimer(self,pCtx):
        lotteryObject = await self.database.find_one({'_id':ObjectId(secrets.lotteryID)})
        endTime = lotteryObject['_lotteryEndTime']
        timeleft = int(endTime - time.time())
        m,s=divmod(timeleft,60)
        h,m=divmod(m,60)
        desc = f'{h:d} hours, {m:02d} minutes, {s:02d} seconds' 
        embed = discord.Embed(title='Lottery Remaining Time', color=0x78BC61, description=desc)
        await pCtx.send(embed=embed)
    
    @commands.command(name='ltotal')
    async def lotteryTotal(self, pCtx):
        lotteryObj = await self.database.find_one({'_id':ObjectId(secrets.lotteryID)})
        amount = float(lotteryObj['_lotteryAmount'])
        embed=discord.Embed(title='Lottery Prize', color=0x78BC61, description=f"The grand prize is currently: £{amount}")
        await pCtx.send(embed=embed)

    @commands.command(aliases=['joinlottery','joinl','lottery'])
    async def joinLot(self,pCtx):
        try:
            player = await self.database.find_one({'_uid':pCtx.message.author.id})
        except Exception as e:
            print(e)
        cursor = self.database.find({'_participants':pCtx.message.author.id})
        participants = await cursor.to_list(length=3)
        if len(participants) > 0:
            embed = discord.Embed(title="Already in Lottery", color=0xF6511D)
            await pCtx.send(embed=embed)
            return
        self.database.update_one({'_id':ObjectId(secrets.lotteryID)}, {'$addToSet':{'_participants':player['_uid']}})
        embed =discord.Embed(title='Successfully added!', color=0x094D92, description=f"You've been added to the lottery")
        await pCtx.send(embed=embed)
    
    async def pickRandomWinner(self, channel, lotteryObject):
        if len(lotteryObject['_participants']) == 0:
            embed = discord.Embed(title='Lottery Delayed', color=0xD4ADCF, description='No contestants in prize pool, rolling again in 5 hours')
            await channel.send(embed=embed)
            self.database.update_one({'_uid':ObjectId(secrets.lotteryID)}, {'$inc':{'_lotteryEndTime':3600}})
            return
        ranIndex = random.randrange(0,len(lotteryObject['_participants']))
        ranWinner = lotteryObject['_participants'][ranIndex]
        embed = discord.Embed(title='Lottery Results!', color=0xD4ADCF)
        lotPrize = lotteryObject['_lotteryAmount']
        embed.add_field(name='Grand Prize', value=f'£{lotPrize}')
        embed.add_field(name='Winner', value=f'<@{ranWinner}>')
        self.database.update_one({'_uid':ranWinner}, {'$inc':{'_currency':lotPrize}})
        self.database.update_one({'_id':ObjectId(secrets.lotteryID)}, {'$set':{'_lotteryAmount':0}})
        endtime = time.time() + lotteryObject['_lotteryLength']
        self.database.update_one({'_id':ObjectId(secrets.lotteryID)}, {'$set':{'_lotteryEndTime':endtime}})
        self.database.update_one({'_id':ObjectId(secrets.lotteryID)}, {'$set':{'_participants':[]}})
        await channel.send(embed=embed)

    async def sendLotteryUpdateMsg(self, channel, lotteryObject, timeleft):
        embed = discord.Embed(title="Lottery!", 
        description='All money lost to the system is returned here in this lottery, every 5 hours!', 
        color=0xD4ADCF, footer="type 'bruh joinl' to join the lottery!")
        amount = lotteryObject['_lotteryAmount']
        m,s=divmod(timeleft,60)
        h,m=divmod(m,60)
        desc = f'{h:d}h, {m:02d}m, {s:02d}s' 
        embed.add_field(name='Current Prize', value=f'£{amount}')
        embed.add_field(name='Time Left',value=f'{desc}')
        await channel.send(embed=embed)

    #@tasks.loop(seconds=0.0,minutes=300.0, hours=0.0, count=None)
    async def lottery(self):
        channel = self.bot.get_channel(secrets.casinoChannel)
        lotteryObject = await self.database.find_one({'_id':ObjectId(secrets.lotteryID)})
        timeleft = int(lotteryObject['_lotteryEndTime'] - time.time())
        if timeleft > 0:
            await self.sendLotteryUpdateMsg(channel, lotteryObject, timeleft)
        elif timeleft <= 0:
            await self.pickRandomWinner(channel, lotteryObject)

    @commands.command()
    async def rollLottery(self,pCtx):
        await self.lottery()
    
    #@lottery.before_loop
    #async def lottery_before(self):
    #    await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(Lottery(bot))