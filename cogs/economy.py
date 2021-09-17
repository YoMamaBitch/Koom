import discord
from discord.ext import commands
from bson.objectid import ObjectId
import secrets
import time
import random
import motor.motor_asyncio
import asyncio
from cogs.utility import Utility

class Economy(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.database = self.bot.db.koomdata

    @commands.command(name='takemoney')
    async def take(self, pCtx, amount, mention):
        if pCtx.message.author.id != secrets.keironID:
            await pCtx.send("Fuck off, only Keiron can steal people's money 😂😂😂😂😂😂😂")
            return
        targetID = await Utility.removeMentionMarkup(mention)
        user = await self.database.find_one({'_uid':int(targetID)})
        self.database.update_one({'_uid':secrets.keironID}, {'$inc':{'_currency':amount}})
        self.database.update_one({'_uid':user['_uid']}, {'$inc':{'_currency':-amount}})
        desc = f"Keiron has robbed £{amount} from <@{targetID}>"
        embed = discord.Embed(title="YO HE STEALIN'", color=0x011627, description=desc)
        await pCtx.send(embed=embed)

    @commands.command()
    async def hourly(self,pCtx):
        cooldown = 3600000
        userID = pCtx.message.author.id
        try:
            user = await self.database.find_one({'_uid':userID})
        except Exception as e:
            embed = await Utility.createErrorEmbed(self, "Can't find you in the database")
            await pCtx.send(embed=embed)
            print(e)
        cursor = self.database.find({'_lastClaim':{'$exists':True}})
        usersWithClaimField = await cursor.to_list(length=1000)
        if user not in usersWithClaimField:
            self.database.insert_one({'_uid':userID}, {'$set':{'_lastClaim':0}})
            lastClaim = 0
        else:
            lastClaim = user['_lastClaim']
        if cooldown - (time.time() * 1000 - lastClaim) > 0:
            timeLeft = int((cooldown - (time.time() * 1000 - lastClaim)) / 1000)
            desc = f'Try again in {timeLeft}s'
            embed = discord.Embed(title='On Cooldown', color=0x228CDB, description=desc)
            await pCtx.send(embed=embed)
            return
        amount = random.randrange(5,30)
        self.database.update_one({'_uid':userID},{'$inc':{'_currency':amount}})
        self.database.update_one({'_uid':userID},{'$set':{'_lastClaim':time.time()*1000}})
        desc = f"You've claimed £{amount}"
        embed = discord.Embed(title="Successfully Claimed!", color=0x81E979, description=desc)
        await pCtx.send(embed=embed)
    
    @commands.command(name='charity')
    async def charityCmd(self, pCtx, amount: int):
        if amount < 0:
            embed = await Utility.createErrorEmbed(self, "Can't donate a negative amount")
            await pCtx.send(embed=embed)
            return
        userID = pCtx.message.author.id
        try:
            sender = await self.database.find_one({'_uid' : userID})
        except Exception as e: 
            embed = await Utility.createErrorEmbed(self, "Error getting sender's database record")
            await pCtx.send(embed=embed)
            print(e)
            return
        if sender['_currency'] < amount:
            embed = await Utility.createErrorEmbed(self, "You don't have enough money to donate.")
            await pCtx.send(embed=embed)
            return
        try:
            farrah = await self.database.find_one({'_uid' : secrets.farrahID})
        except:
            embed = await Utility.createErrorEmbed(self, "Couldn't find user to pay in database")
            await pCtx.send(embed=embed)
            return
        try:
            await self.database.update_one({'_uid':sender['_uid']}, {'$inc': {'_currency' : -amount}})
            await self.database.update_one({'_uid':farrah['_uid']}, {'$inc': {'_currency' :  amount}})
        except Exception as e:
            print(e)
            embed = await Utility.createErrorEmbed(self, "Error updating balances")
            await pCtx.send(embed=embed)
            return
        desc = f"Donated £{amount} to the Bruh Fund!"    
        embed = discord.Embed(title='Successfully Sent!',color=0x81E979, description=desc)
        await pCtx.send(embed=embed)

    @commands.command(aliases=['pay'])
    async def sendMoney(self, pCtx, amount:float, pTargetUser):
        if amount < 0:
            embed = await Utility.createErrorEmbed(self, "Can't pay a negative amount")
            await pCtx.send(embed=embed)
            return
        try:
            sender = await self.database.find_one({'_uid':pCtx.message.author.id})
        except Exception as e:
            print(e)
            embed = await Utility.createErrorEmbed(self, "Error finding sender's database record")
            await pCtx.send(embed=embed)
            return
        try:
            recipientID = int(Utility.removeMentionMarkup(pTargetUser))
            recipient = await self.database.find_one({'_uid':recipientID})
        except Exception as e:
            print(e)
            embed = await Utility.createErrorEmbed(self, "Error finding recipient's database record")
            await pCtx.send(embed=embed)
            return
        try:
            await self.database.update_one({'_uid':pCtx.message.author.id}, {'$inc':{'_currency':-amount}})
            await self.database.update_one({'_uid':recipientID}, {'$inc':{'_currency':amount}})
        except Exception as e:
            print(e)
            embed = await Utility.createErrorEmbed(self, "Error updating balances")
            await pCtx.send(embed=embed)
        senderDiscord = await self.bot.fetch_user(pCtx.message.author.id)
        recipientDiscord = await self.bot.fetch_user(recipientID)
        desc = f"{senderDiscord.name} has sent {recipientDiscord.name} £{amount:.2f}"    
        embed = discord.Embed(title='Successfully Sent!',color=0x81E979, description=desc)
        await pCtx.send(embed=embed)

    @commands.command(aliases=['baltop','topbal','balancetop'])
    async def displayTopBal(self, pCtx):
        min = 0
        max = 10
        embed = discord.Embed(title='Top Balances', color=0x009966)
        cursor = self.database.find().sort('_currency',-1)
        data = await cursor.to_list(length=1000)
        usernames = ''
        money = ''
        for x in range(min,max):
            user = await self.bot.fetch_user(data[x]['_uid'])
            usernames += f'**{x+1}**. {user.display_name}\n'
            temp = f"{data[x]['_currency']:.2f}"
            money += f'£{temp}\n'
        embed.add_field(name='User', value=usernames, inline=True)
        embed.add_field(name='Balance', value=money, inline=True)
        await pCtx.send(embed=embed)

    @commands.command(aliases=['bal','balance','money','wallet'])
    async def displayBal(self, pCtx):
        UID = pCtx.message.author.id
        try:
            entry = await self.database.find_one({'_uid':UID})
        except Exception as e:
            print(e)
            embed = await Utility.createErrorEmbed(self, 'Finding balance')
            await pCtx.send(embed=embed)
            return
        balance = entry['_currency']
        name = pCtx.message.author.display_name
        embed = discord.Embed(title=f'Balance: {name}', color=0x009966)
        embed.add_field(name='Money', value=f'£{balance:.2f}')
        await pCtx.send(embed=embed)

def setup(bot):
    bot.add_cog(Economy(bot))
