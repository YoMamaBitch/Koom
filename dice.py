import discord
import asyncio
import motor.motor_asyncio
from bson.objectid import ObjectId
import secrets
import random

class Dice():
    def __init__(self, bot, message, amount:int = 0):
        self.bot = bot
        self.channel = message.channel
        self.message = message.content
        self.userid = message.author.id
        self.amount = amount
        self.dicedb = bot.db.dicedata
        self.db = bot.db.koomdata

    async def start(self):
        if not await self.checkIfInDB():
            return
        uconfig = await self.dicedb.find_one({'_uid':self.userid})
        result = self.rolldice()
        if result > uconfig['_roll']:
            await self.sendWinMsg(result, uconfig['_roll'], uconfig['_payout'])
        else:
            await self.sendLoseMsg(result, uconfig['_roll'])
            self.amount = -self.amount
        await self.updateBalance()

    async def updateBalance(self):
        if self.amount < 0:
            await self.db.update_one({'_uid':self.userid}, {'$inc':{'_currency':self.amount}})
            await self.db.update_one({'_id':ObjectId(secrets.lotteryAmount)}, {'$inc':{'_lotteryAmount':(-self.amount * secrets.tax)}})
        else:
            config = await self.dicedb.find_one({'_uid':self.userid})
            payout = config['_payout']
            scaledAmount = self.amount * (payout-1.0)
            userdata = await self.db.find_one({'_uid':self.userid})
            newCurrency = userdata['_currency'] + scaledAmount
            await self.db.update_one({'_uid':self.userid}, {'$set':{'_currency':newCurrency}})

    async def sendLoseMsg(self, result, rollover):
        desc  = f"You rolled: **{result}**\nYou needed to roll over: **{rollover:.2f}** to win\n**£{self.amount}** has been taken from your account."
        embed = discord.Embed(title='Lose', color=0xDA2C38, description=desc)
        await self.channel.send(embed=embed)

    async def sendWinMsg(self, result, rollover, payout):
        scaledPayout = (payout-1.0) * self.amount
        desc = f"You rolled: **{result}**\nYou needed to roll over: **{rollover:.2f}** to win\n**£{scaledPayout:.2f}** has been added to your account."
        embed = discord.Embed(title='Win', color=0x226F54, description=desc)
        await self.channel.send(embed=embed)

    def rolldice(self):
        return random.randrange(0,100000) / 1000

    async def checkIfInDB(self):
        userconfig = await self.dicedb.find_one({'_uid':self.userid})
        if userconfig == None:
            await self.generateConfig()
            desc = f"I've generated a dice config for you as you didn't have one, edit it using 'bruh configdice'"
            embed = discord.Embed(title='Dice Config', color=0x252422, description=desc)
            await self.channel.send(embed=embed)
            return False
        return True

    async def generateConfig(self):
        doc = {'_uid':self.userid,
                '_roll':50.49,
                '_payout':2.000}
        await self.dicedb.insert_one(doc)    
        
    async def displayConfig(self):
        await self.checkIfInDB()
        uConfig = await self.dicedb.find_one({'_uid':self.userid})
        rollover = uConfig['_roll']
        payout = uConfig['_payout']
        desc = f"Your roll over number is **{rollover:.2f}**, you must roll above this value to win\nYour payout is **{payout:.3f}x**, meaning your bet will get multipled by this on a win\n"
        desc += f"Edit your roll over number via **'bruh configroll NEWROLLOVER'**\nEdit your payout by typing **'bruh configpayout NEWPAYOUT'**"
        embed = discord.Embed(title='Dice Config', color=0x465775, description=desc)
        await self.channel.send(embed=embed)

    async def updateConfigRoll(self, newRoll):
        await self.checkIfInDB()
        newRoll = float(newRoll)
        if newRoll >= 99.999 or newRoll <= 0.0:
            embed = discord.Embed(title='Error', color=0xD00000, description='Invalid roll input, needs to be < 99.999 and > 0')
            await self.channel.send(embed=embed)
            return
        newPayout = 100.0 / (100.0-newRoll)
        await self.dicedb.update_one({'_uid':self.userid}, {'$set':{'_roll':newRoll}})
        await self.dicedb.update_one({'_uid':self.userid}, {'$set':{'_payout':newPayout}})
        desc = f"Your new roll over number is {newRoll:.2f}, the payout is {newPayout:.3f}x"
        embed = discord.Embed(title='Config Updated', color=0x623CEA, description=desc)
        await self.channel.send(embed=embed)

    async def updateConfigPayout(self, newPayout):
        await self.checkIfInDB()
        newPayout = float(newPayout)
        if newPayout <= 0.0 or newPayout > 9999:
            embed = discord.Embed(title='Error' , color=0xD00000, description='Invalid payout input, needs to be > 0 and <= 9999')
            await self.channel.send(embed=embed)
            return
        newRoll = 100.0-(100.0/newPayout)
        await self.dicedb.update_one({'_uid':self.userid}, {'$set':{'_roll':newRoll}})
        await self.dicedb.update_one({'_uid':self.userid}, {'$set':{'_payout':newPayout}})
        desc=f"Your new roll over number is {newRoll:.2f}, the payout is {newPayout:.3f}x"
        embed = discord.Embed(title='Config Updated', color=0x623CEA, description=desc)
        await self.channel.send(embed=embed)

        



