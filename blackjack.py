from os import name
import discord
from discord.colour import Color
from discord.ext import commands
import asyncio
import motor.motor_asyncio
import secrets
import random

playingCards = {'A':1,'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'10':10,'J':10,'K':10,'Q':10}

class BlackjackGame():
    def __init__(self, bot, message, amount:int, bjSessions):
        self.bot = bot
        self.message = message
        self.messageChannel = message.channel
        self.amount = amount
        self.sessions = bjSessions
        self.player = message.author.id
        self.playerhand = []
        self.dealerhand =  []
        self.dealerStopped = False
    
    async def start(self):
        await self.hitPlayer()
        await self.hitPlayer()
        await self.sendHitMessage()

    async def update(self, reaction, user):
        if (reaction.message.id != self.message.id) or (user.id != self.player):
            return
        if reaction.emoji == '🇸':
            await self.standPlayer()
        elif reaction.emoji == '🇭':
            await self.hitPlayer()

    async def sendHitMessage(self):
        hand = self.getHandString(self.playerhand)
        user = await self.bot.fetch_user(self.player)
        name = user.display_name
        pp = user.avatar_url.BASE + user.avatar_url._url
        try:
            embed = discord.Embed(title="Hit?",description='Would you like to hit?', color=0xDB2763)
            embed.set_author(name=name, url=discord.Embed.Empty, icon_url=pp)
        except Exception as e:
            print(e)
        embed.add_field(name='Dealer First Card:',value=self.dealerhand[0], inline=False)
        embed.add_field(name='Your Hand:',value=f'{hand}')
        msg = await self.message.channel.send(embed=embed)
        self.message = msg
        await msg.add_reaction('🇸')
        await msg.add_reaction('🇭')

    async def standPlayer(self):
        while self.valueOfHand(self.dealerhand) < 17:
            await self.hitDealer()
        if self not in self.sessions:
            return
        valuePlayer = self.valueOfHand(self.playerhand)
        valueDealer = self.valueOfHand(self.dealerhand)
        if valuePlayer > valueDealer:
            await self.playerWin()
        elif valuePlayer == valueDealer:
            await self.draw()
        else:
            await self.playerLose()
        
    async def standDealer(self):
        self.dealerStopped = True
        embed = discord.Embed(title='Dealer Has Stopped', color=0xFFD400)
        await self.messageChannel.send(embed=embed)

    async def updateDealer(self):
        if self.valueOfHand(self.dealerhand) < 17:
            await self.hitDealer()
        elif not self.dealerStopped:
            await self.standDealer()
        if len(self.playerhand) > 2 and self in self.sessions:
            await self.sendHitMessage()

    async def draw(self):
        embed = discord.Embed(title="It's a draw!", color=0x2F1847)
        embed.add_field(name='Dealer Hand:',value=self.getHandString(self.dealerhand),inline=False)
        embed.add_field(name='Player Hand:',value=self.getHandString(self.playerhand))
        await self.messageChannel.send(embed=embed)
        self.sessions.remove(self)

    async def playerLose(self):
        userObject = await self.bot.db.koomdata.find_one({'_uid':self.player})
        newMoney = userObject['_currency'] - int(self.amount)
        self.bot.db.koomdata.update_one({'_uid':self.player}, {'$set':{'_currency':newMoney}})
        embed = discord.Embed(title='You Lose', color=0xD00000, description='Better luck next time')
        dealerHand = self.getHandString(self.dealerhand)
        playerHand = self.getHandString(self.playerhand)
        embed.add_field(name='Dealer Hand:',value=dealerHand)
        embed.add_field(name='Your Hand: ',value=playerHand,inline=False)
        await self.messageChannel.send(embed=embed)
        self.sessions.remove(self)

    async def playerWin(self):
        userObject = await self.bot.db.koomdata.find_one({'_uid':self.player})
        newMoney = userObject['_currency']+ int(self.amount)
        self.bot.db.koomdata.update_one({'_uid':self.player}, {'$set':{'_currency':newMoney}})
        embed = discord.Embed(title='You win!', color=0x81E979)
        embed.add_field(name='Dealer Hand:',value=self.getHandString(self.dealerhand))
        embed.add_field(name='Your Hand: ',value=self.getHandString(self.playerhand),inline=False)
        await self.messageChannel.send(embed=embed)
        self.sessions.remove(self)

    async def hitPlayer(self):
        r1 = random.randrange(0,13)
        self.playerhand.append([*playingCards][r1])
        try:
            sumOfCards = self.valueOfHand(self.playerhand)
        except Exception as e:
            print(e)
        if sumOfCards > 21:
            await self.playerBust()
            return
        await self.updateDealer()
        
    async def hitDealer(self):
        r1 = random.randrange(0,13)
        self.dealerhand.append([*playingCards][r1])
        sumOfCards = self.valueOfHand(self.dealerhand)
        if sumOfCards > 21:
            await self.dealerBust()

    async def playerBust(self):
        userObject = await self.bot.db.koomdata.find_one({'_uid':self.player})
        newMoney = userObject['_currency'] - int(self.amount)
        self.bot.db.koomdata.update_one({'_uid':self.player}, {'$set':{'_currency':newMoney}})
        embed = discord.Embed(title='You went Bust!', color=0xD00000, description='Better luck next time bucko')
        embed.add_field(name='Your Hand',value=self.getHandString(self.playerhand))
        await self.messageChannel.send(embed=embed)
        self.sessions.remove(self)

    async def dealerBust(self):
        userObject = await self.bot.db.koomdata.find_one({'_uid':self.player})
        newMoney = userObject['_currency'] + int(self.amount)
        self.bot.db.koomdata.update_one({'_uid':self.player}, {'$set':{'_currency':newMoney}})
        embed = discord.Embed(title='Dealer Bust!', description=f'Congrats, you win £{self.amount}!', color=0x81E979)
        embed.add_field(name='Dealer Hand:', value=self.getHandString(self.dealerhand))
        await self.messageChannel.send(embed=embed)
        self.sessions.remove(self)

    def getHandString(self, hand):
        strr = ''
        for card in hand:
            strr += card + ' '
        return strr

    def valueOfHand(self, hand):
        total = 0
        for card in hand:
            total += playingCards[card]
        return total