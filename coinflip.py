import discord
import asyncio
import motor.motor_asyncio
from bson.objectid import ObjectId
import secrets
import random
from cogs.utility import Utility

class Coinflip():
    def __init__(self, bot, message, guess, amount:int, otherPlayer):
        self.bot = bot
        self.amount = amount
        self.message = message
        self.player = message.author.id
        self.otherPlayer = otherPlayer
        self.guess = str.lower(guess)
        self.headList = ['heads','head','ct','h']
        self.tailList = ['tails','tail','t','t']
    
    async def updateBalance(self,amount, UID):
        self.bot.db.koomdata.update_one({'_uid':UID}, {'$inc':{'_currency':amount}})

    async def pvpFlip(self, result, msg):
        try:
            target = await Utility.fetchFromMention(self, self.otherPlayer)
        except Exception as e:
            embed = discord.Embed(title="Error", color=0xC5283D, description='Problem finding other user, retry.\nSometimes caused by copy+pasting an @SOMEONE')
            await msg.edit(embed=embed)
            return
        if target.id == self.player:
            embed = discord.Embed(title='Wait a minute fucko', color=0xB9314F,
                description="You can't coinflip against yourself!")
            await msg.edit(embed=embed)
            return
        try:
            targetDoc = await self.bot.db.koomdata.find_one({'_uid':target.id})
        except Exception as e:
            print(e)
        if targetDoc['_currency'] < self.amount:
            embed = discord.Embed(title='Wait a minute fucko', color=0xB9314F,
                description=f"{target.display_name} does not have enough money")
            await msg.edit(embed=embed)
            return

        p1WinBal = self.player['_currency'] + self.amount
        p1LossBal = self.player['_currency'] - self.amount
        p2WinBal = targetDoc['_currency'] + self.amount
        p2LossBal = targetDoc['_currency'] - self.amount
        winText = f'{self.message.author.display_name}, £{self.amount} has been added to your account.\nBalance: £{p1WinBal:.2f}\n\n'
        winText += f'{target.display_name}, £{self.amount} has been taken from your account.\nBalance: £{p2LossBal:.2f}'
        loseText = f'{self.message.author.display_name}, £{self.amount} has been taken from your account.\nBalance: £{p1LossBal:.2f}\n\n'
        loseText += f'{target.display_name}, £{self.amount} has been added to your account.\nBalance: £{p2WinBal:.2f}'

        if result > 500000 and self.guess in self.headList:
            embed = discord.Embed(title=f'{self.message.author.display_name} Wins!', 
                color=0xF34213,description=winText)
            await self.updateBalance(self.amount, self.player['_uid'])
            await self.updateBalance(-self.amount, targetDoc['_uid'])
        elif result <= 500000 and self.guess in self.tailList:
            embed = discord.Embed(title=f'{self.message.author.display_name} Wins!', color=0xF34213,description=winText)
            await self.updateBalance(self.amount, self.player['_uid'])
            await self.updateBalance(-self.amount, targetDoc['_uid'])
        else:
            embed = discord.Embed(title=f'{target.display_name} Wins!', color=0xF34213,description=loseText)
            await self.updateBalance(self.amount, targetDoc['_uid'])
            await self.updateBalance(-self.amount, self.player['_uid'])
        await msg.edit(embed=embed)

    async def botFlip(self, result,msg):
        prevBal = self.player['_currency']
        newBalWin = prevBal + self.amount
        newBalLoss = prevBal - self.amount
        winText = f'£{self.amount} has been added to your account. Your new balance is £{newBalWin:.2f}'
        loseText = f'£{self.amount} has been taken from your account. Your new balance is £{newBalLoss:.2f}'
        if result > 500000 and self.guess in self.headList:
            embed = discord.Embed(title='You Win!', color=0xB43E8F,description=winText)
            await self.updateBalance(self.amount, self.player['_uid'])
        elif result <= 500000 and self.guess in self.tailList:
            embed = discord.Embed(title='You Win!', color=0xB43E8F,description=winText)
            await self.updateBalance(self.amount, self.player['_uid'])
        else:
            embed = discord.Embed(title='You Lose', color=0x750D37,description=loseText)
            await self.updateBalance(-self.amount, self.player['_uid'])
            await self.bot.db.koomdata.update_one({'_id':ObjectId(secrets.lotteryID)}, {'$inc':{'_lotteryAmount':self.amount * secrets.tax}})

        await msg.edit(embed=embed)

    async def flip(self):
        embed = discord.Embed(title='Flipping...',color=0x4FB0C6 )
        msg = await self.message.channel.send(embed=embed)
        await asyncio.sleep(random.randrange(3,6))
        result = random.randrange(0,999999)
        if self.otherPlayer == None:
            await self.botFlip(result,msg)
        else:
            await self.pvpFlip(result,msg)

    async def start(self):
        if self.amount < 0:
            await self.message.channel.send("Can't bet a negative amount")
            return
        if self.guess not in self.headList and self.guess not in self.tailList:
            await self.message.channel.send("Invalid guess")
            return
        try:
            uid = self.player
            self.player = await self.bot.db.koomdata.find_one({'_uid':uid})
        except Exception as e:
            print(e)
            return
        if self.player['_currency'] < self.amount:
            await self.message.channel.send("Not enough money to start bet")
            return
        await self.flip()
