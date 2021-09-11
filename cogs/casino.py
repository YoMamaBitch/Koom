import asyncio
import discord
from discord.ext import commands
import motor.motor_asyncio
import random
import secrets
import time

class Casino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = []
        self.bot.mongo = motor.motor_asyncio.AsyncIOMotorClient(str(secrets.mongoKey))
        self.bot.db = self.bot.mongo.userdata


    @commands.Cog.listener()
    async def on_command_error(self, pCtx, error):
        if isinstance(error, commands.CommandOnCooldown):
            msg = '**On Cooldown!** Try again in {:.2f}s'.format(error.retry_after)
            await pCtx.send(msg)

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
    async def cf(self, pCtx, amount, guess):
        guess = str.lower(guess)
        headsList = ['heads','head','ct']
        tailsList = ['tails','tail','t']
        if guess not in headsList and guess not in tailsList:
            await pCtx.send("Invalid input")
            return
        uID = pCtx.message.author.id
        try:
            gambler = await self.bot.db.koomdata.find_one({'_uid' : uID})
        except Exception as e:
            print(e)
            return
        if gambler['_currency'] < int(amount):
            await pCtx.send("Not enough money to bet")
            return
        await pCtx.send("Starting flip:")
        await asyncio.sleep(random.randrange(2,5))
        outcome = random.choice([0,1])
        winner = False
        if outcome == 0 and guess in headsList:
            await pCtx.send("You Win! - New Bal: %s" % str(gambler['_currency'] + int(amount)))
            winner = True
        elif outcome == 1 and guess in tailsList:
            await pCtx.send("You win! - New Bal: %s" % str(gambler['_currency'] + int(amount)))
            winner = True
        else:
            await pCtx.send("You lose - New Bal: %s" % str(gambler['_currency'] - int(amount)))
        if winner:
            self.bot.db.koomdata.update_one({'_uid':gambler['_uid']}, {'$set': {'_currency' :  gambler['_currency'] + int(amount)}})
        else:
            self.bot.db.koomdata.update_one({'_uid':gambler['_uid']}, {'$set': {'_currency' :  gambler['_currency'] - int(amount)}})

    @commands.command(name='pay')
    async def send(self, pCtx, amount, pTarget):
        userID = pCtx.message.author.id
        payer = None
        payee = None
        try:
            payer = await self.bot.db.koomdata.find_one({'_uid' : userID})
        except:
            return
        if (payer['_currency'] < int(amount)):
            await pCtx.send("You don't have enough money.")
            return
        try:
            strr = pTarget[3:len(pTarget)-1]
            payee = await self.bot.db.koomdata.find_one({'_uid' : int(strr)})
        except:
            await pCtx.send("Error: Couldn't find user to pay in system")
            return
        try:
            self.bot.db.koomdata.update_one({'_uid':payer['_uid']}, {'$set': {'_currency' :  payer['_currency']-int(amount)}})
            self.bot.db.koomdata.update_one({'_uid':payee['_uid']}, {'$set': {'_currency' :  payee['_currency']+int(amount)}})
        except:
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

    @commands.command()
    async def start(self, pCtx):
        if pCtx.message.author.id != 241716281961742336:
            return
        self.bot.cursor = self.bot.db.koomdata.find({})
        existingUsers = await self.bot.cursor.to_list(length=1000)
        newUsers = []
        for member in pCtx.guild.members:
            if self.in_dict('_uid', member.id, existingUsers) == {}:
                newUsers.append(member.id)
            else:
                continue
        for user in newUsers:
            self.bot.db.koomdata.insert_one({'_uid':user, '_currency':100})

    def in_dict(self, key,value,dict):
        for entry in dict:
            if entry[key] == value:
                return entry
        return {}

def setup(bot):
    bot.add_cog(Casino(bot))