import asyncio
from coinflip import Coinflip
import discord
from discord import user
from discord.ext import commands
from discord.ext import tasks
import motor.motor_asyncio
import random
import secrets
import time
from bson.objectid import ObjectId
import blackjack

cards = {'A':1,'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'10':10,'J':10,'K':10,'Q':10}

class Casino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = []
        self.bjSessions = []
        self.bot.mongo = motor.motor_asyncio.AsyncIOMotorClient(str(secrets.mongoKey))
        self.bot.db = self.bot.mongo.userdata
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
        else:
            ranIndex = random.randrange(-1,len(lotteryObject['_participants']))
            ranWinner = lotteryObject['_participants'][ranIndex]
            embed = discord.Embed(title='Lottery Results!', color=0xD4ADCF)
            lotPrize = lotteryObject['_lotteryAmount']
            embed.add_field(name='GrandPrize', value=f'Grand Prize: £{lotPrize}')
            embed.add_field(name='Winner', value=f'Winner: <@{ranWinner}>')
            winner = await self.bot.db.koomdata.find_one({'_uid':ranWinner})
            newCurrency = winner['_currency'] + lotPrize
            await self.bot.db.koomdata.update_one({'_uid':ranWinner}, {'$set':{'_currency':newCurrency}})
            await self.bot.db.koomdata.update_one({'_id':ObjectId('613ce2090e01049878d07fb5')}, {'$set':{'_lotteryAmount':0}})
            endtime = time.time() + lotteryObject['_lotteryLength']
            await self.bot.db.koomdata.update_one({'_id':ObjectId('613ce2090e01049878d07fb5')}, {'$set':{'_lotteryEndTime':endtime}})
            await self.bot.db.koomdata.update_one({'_id':ObjectId('613ce2090e01049878d07fb5')}, {'$set':{'_participants':[]}})
        await channel.send(embed=embed)

    @lottery.before_loop
    async def lottery_before(self):
        await self.bot.wait_until_ready()

    @commands.command(name='takeMoney')
    async def take(self, pCtx, amount, mention):
        if pCtx.message.author.id != secrets.keironID:
            await pCtx.send("Fuck off. Only Keiron can use this command")
            return
        if '!' in mention:
            ID = mention[3:len(mention)-1]
        else:
            ID = mention[2:len(mention)-1]
        keiron = await self.bot.db.koomdata.find_one({'_uid' : secrets.keironID})
        user = await self.bot.db.koomdata.find_one({'_uid' : int(ID)})
        kNewMoney = int(amount) + keiron['_currency']
        uNewMoney = user['_currency'] - int(amount)
        self.bot.db.koomdata.update_one({'_uid':keiron['_uid']}, {'$set': {'_currency' :  kNewMoney}})
        self.bot.db.koomdata.update_one({'_uid':user['_uid']}, {'$set': {'_currency' :  uNewMoney}})
        await pCtx.send(f"Keiron has robbed £{amount} from <@{ID}>")

    @commands.command(name='baltop')
    async def balancetop(self, pCtx):
        embed = discord.Embed(title='Top Balances', color=0x009966)
        cursor = self.bot.db.koomdata.find().sort('_currency',-1)
        data = await cursor.to_list(length=1000)
        usernames = ''
        money = ''
        for x in range(0,10):
            user = await self.bot.fetch_user(data[x]['_uid'])
            usernames += f'**{x+1}**. {user.display_name}\n'
            temp = str(data[x]['_currency'])
            money += f'£{temp}\n'
        embed.add_field(name='Person', value=usernames, inline=True)
        embed.add_field(name='Balance', value=money, inline=True)
        await pCtx.send(embed=embed)

    @commands.command()
    async def hourly(self, pCtx):
        cooldown = 3600000
        userID = pCtx.message.author.id
        try:
            user = await self.bot.db.koomdata.find_one({'_uid' : userID})
        except Exception as e:
            print(e)
            return
        cursor = self.bot.db.koomdata.find({'_lastClaim':{'$exists':True}})
        usersWithClaimField = await cursor.to_list(length=1000)
        if user not in usersWithClaimField:
            self.bot.db.koomdata.insert_one({'_uid':user['_uid']}, {'$set': {'_lastClaim' : 0}})
            lastClaim = 0
        else:
            lastClaim = user['_lastClaim']
        if cooldown - (time.time() * 1000 - lastClaim) > 0:
            await pCtx.send('**On Cooldown!** Try again in %is' % int((cooldown - (time.time() * 1000 - lastClaim)) / 1000))
            return
        
        amount = random.randrange(5,30)
        self.bot.db.koomdata.update_one({'_uid':user['_uid']}, {'$set': {'_currency' :  user['_currency'] + int(amount)}})
        self.bot.db.koomdata.update_one({'_uid':user['_uid']}, {'$set': {'_lastClaim' :  time.time() * 1000}})
        await pCtx.send("You've claimed £%s!" % int(amount))            

    @commands.command(name='coinflip')
    async def cf(self, pCtx, amount : int, guess, otherPlayer = None):
        game = Coinflip(self.bot, pCtx.message, guess, amount, otherPlayer)
        await game.start()

    @commands.command(name='charity')
    async def charityCmd(self, pCtx, amount: int):
        if amount < 0:
            await pCtx.send("Can't pay negative amount")
            return
        userID = pCtx.message.author.id
        try:
            payer = await self.bot.db.koomdata.find_one({'_uid' : userID})
        except Exception as e: 
            print(e)
            return
        if payer['_currency'] < amount:
            await pCtx.send("You don't have enough money.")
            return
        try:
            farrah = await self.bot.db.koomdata.find_one({'_uid' : 278288530143444993})
        except:
            await pCtx.send("Error: Couldn't find user to pay in system")
            return
        try:
            payerNew = payer['_currency'] - int(amount)
            payeeNew = farrah['_currency'] + int(amount)
            await self.bot.db.koomdata.update_one({'_uid':payer['_uid']}, {'$set': {'_currency' : payerNew}})
            await self.bot.db.koomdata.update_one({'_uid':farrah['_uid']}, {'$set': {'_currency' :  payeeNew}})
        except Exception as e:
            print(e)
            await pCtx.send("Error updating balances")
            return
        await pCtx.send(":white_check_mark: Successfully donated to the Bruh Fund!")

    @commands.command(name='pay')
    async def send(self, pCtx, amount : int, pTarget):
        if amount < 0:
            await pCtx.send("Can't pay a negative amount")
            return
        userID = pCtx.message.author.id
        payer = None
        payee = None
        try:
            payer = await self.bot.db.koomdata.find_one({'_uid' : userID})
        except Exception as e: 
            print(e)
            return
        payerCurrency = int(payer['_currency'])
        if payerCurrency < amount:
            await pCtx.send("You don't have enough money.")
            return
        try:
            if '!' in pTarget:
                strr = pTarget[3:len(pTarget)-1]
            else:
                strr = pTarget[2:len(pTarget)-1]
            payee = await self.bot.db.koomdata.find_one({'_uid' : int(strr)})
        except:
            await pCtx.send("Error: Couldn't find user to pay in system")
            return
        try:
            payerNew = payer['_currency'] - int(amount)
            payeeNew = payee['_currency'] + int(amount)
            await self.bot.db.koomdata.update_one({'_uid':payer['_uid']}, {'$set': {'_currency' : payerNew}})
            await self.bot.db.koomdata.update_one({'_uid':payee['_uid']}, {'$set': {'_currency' :  payeeNew}})
        except Exception as e:
            print(e)
            await pCtx.send("Error updating balances")
            return
        await pCtx.send(":white_check_mark: Successfully Sent!")
        
    @commands.command(aliases=['bal','money'])
    async def balance(self, pCtx):
        userID = pCtx.message.author.id
        try:
            doc = await self.bot.db.koomdata.find_one({'_uid' : userID})
        except Exception as e:
            print(e)
            return
        embed = discord.Embed(title='User Balance: %s' % pCtx.message.author.display_name, color=0x009966)
        embed.add_field(name='Money', value='£%s'%doc['_currency'])
        await pCtx.send(embed=embed)

    def in_dict(self, key,value,dict):
        for entry in dict:
            if entry[key] == value:
                return entry
        return {}

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