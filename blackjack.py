import discord
from discord.ext import commands
import asyncio
import motor.motor_asyncio
from bson.objectid import ObjectId
import secrets
import random

class BlackjackGame():
    def __init__(self, bot, message, amount:int, bjSessions):
        self.bot = bot
        self.message = message
        self.messageChannel = message.channel
        self.outMsg = None
        self.amount = amount
        self.sessions = bjSessions
        self.player = message.author.id
        self.playerhand = []
        self.dealerhand =  []
        self.dealerStopped = False
        self.deck = [('A',11),('2',2),('3',3),('4',4),('5',5),('6',6),('7',7),('8',8),('9',9),('10',10),('J',10),('Q',10),('K',10),
        ('A',11),('2',2),('3',3),('4',4),('5',5),('6',6),('7',7),('8',8),('9',9),('10',10),('J',10),('Q',10),('K',10),
        ('A',11),('2',2),('3',3),('4',4),('5',5),('6',6),('7',7),('8',8),('9',9),('10',10),('J',10),('Q',10),('K',10),
        ('A',11),('2',2),('3',3),('4',4),('5',5),('6',6),('7',7),('8',8),('9',9),('10',10),('J',10),('Q',10),('K',10)]

        random.shuffle(self.deck)
        random.shuffle(self.deck)
    
    async def start(self):
        await self.hitDealer()
        await self.hitPlayer()
        await self.hitPlayer()
        #await self.sendHitMessage()

    async def update(self, reaction, user):
        if (reaction.message.id != self.outMsg.id) or (user.id != self.player):
            return
        if reaction.emoji == '🇸':
            await self.standPlayer()
        elif reaction.emoji == '🇭':
            await self.hitPlayer()

    async def sendHitMessage(self):
        hand = self.getHandString(self.playerhand)
        value = self.valueOfHand(self.playerhand)
        hand += f'\nValue={value}'
        user = await self.bot.fetch_user(self.player)
        name = user.display_name
        pp = user.avatar_url.BASE + user.avatar_url._url
        try:
            embed = discord.Embed(title="Hit?",description='\u200b', color=0xDB2763)
            embed.set_author(name=name, url=discord.Embed.Empty, icon_url=pp)
        except Exception as e:
            print(e)
        text = self.dealerhand[0][0]
        embed.add_field(name='Dealer First Card:',value=text, inline=False)
        embed.add_field(name='Your Hand:',value=f'{hand}')
        if (self.outMsg == None):
            self.outMsg = await self.message.channel.send(embed=embed)
            await self.outMsg.add_reaction('🇸')
            await self.outMsg.add_reaction('🇭')
            return
        await self.outMsg.edit(embed=embed)

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
        await self.outMsg.edit(embed=embed)
        self.sessions.remove(self)

    async def playerLose(self):
        userObject = await self.bot.db.koomdata.find_one({'_uid':self.player})
        newMoney = userObject['_currency'] - int(self.amount)
        self.bot.db.koomdata.update_one({'_uid':self.player}, {'$set':{'_currency':newMoney}})
        self.bot.db.koomdata.update_one({'_id':ObjectId(secrets.lotteryAmount)}, {'$inc':{'_lotteryAmount':int(self.amount)}})
        embed = discord.Embed(title='You Lose', color=0xD00000, description='Better luck next time')
        dealerHand = self.getHandString(self.dealerhand)
        playerHand = self.getHandString(self.playerhand)
        embed.add_field(name='Dealer Hand:',value=dealerHand)
        embed.add_field(name='Your Hand: ',value=playerHand,inline=False)
        await self.outMsg.edit(embed=embed)
        self.sessions.remove(self)

    async def playerWin(self):
        userObject = await self.bot.db.koomdata.find_one({'_uid':self.player})
        newMoney = userObject['_currency']+ int(self.amount)
        self.bot.db.koomdata.update_one({'_uid':self.player}, {'$set':{'_currency':newMoney}})
        embed = discord.Embed(title='You win!', color=0x81E979)
        embed.add_field(name='Dealer Hand:',value=self.getHandString(self.dealerhand))
        embed.add_field(name='Your Hand: ',value=self.getHandString(self.playerhand),inline=False)
        await self.outMsg.edit(embed=embed)
        self.sessions.remove(self)

    async def checkIfPlayerBust(self):
        sumOfCards = self.valueOfHand(self.playerhand)
        try:
            if sumOfCards > 21:
                while ('A',11) in self.playerhand:
                    self.playerhand.remove(('A',11))
                    self.playerhand.append(('A',1))
                    if self.valueOfHand(self.playerhand) <= 21:
                        await self.sendHitMessage()
                        return
                await self.playerBust()
                return
        except Exception as e:
            print(e)
        if len(self.playerhand) > 1:
            await self.sendHitMessage()
        return False

    async def hitPlayer(self):
        c1 = random.choice([*self.deck])
        self.deck.remove(c1)
        self.playerhand.append(c1)
        await self.checkIfPlayerBust()
        
    async def checkIfDealerBust(self):
        sumOfCards = self.valueOfHand(self.dealerhand)
        try:
            if sumOfCards > 21:
                while ('A',11) in self.dealerhand:
                    self.dealerhand.remove(('A',11))
                    self.dealerhand.append(('A',1))
                    if self.valueOfHand(self.dealerhand) <= 21:
                        return
                await self.dealerBust()
        except Exception as e:
            print(e)
        return False

    async def hitDealer(self):
        c1 = random.choice([*self.deck])
        self.deck.remove(c1)
        self.dealerhand.append(c1)
        await self.checkIfDealerBust()

    async def playerBust(self):
        userObject = await self.bot.db.koomdata.find_one({'_uid':self.player})
        newMoney = userObject['_currency'] - int(self.amount)
        self.bot.db.koomdata.update_one({'_uid':self.player}, {'$set':{'_currency':newMoney}})
        self.bot.db.koomdata.update_one({'_id':ObjectId(secrets.lotteryAmount)}, {'$inc':{'_lotteryAmount':int(self.amount)}})
        embed = discord.Embed(title='You went Bust!', color=0xD00000, description='Better luck next time bucko')
        embed.add_field(name='Your Hand',value=self.getHandString(self.playerhand))
        await self.outMsg.edit(embed=embed)
        self.sessions.remove(self)

    async def dealerBust(self):
        userObject = await self.bot.db.koomdata.find_one({'_uid':self.player})
        newMoney = userObject['_currency'] + int(self.amount)
        self.bot.db.koomdata.update_one({'_uid':self.player}, {'$set':{'_currency':newMoney}})
        embed = discord.Embed(title='Dealer Bust!', description=f'Congrats, you win £{self.amount}!', color=0x81E979)
        embed.add_field(name='Dealer Hand:', value=self.getHandString(self.dealerhand))
        embed.add_field(name='Your Hand:', value=self.getHandString(self.playerhand), inline=False)
        await self.outMsg.edit(embed=embed)
        self.sessions.remove(self)

    def getHandString(self, hand):
        strr = ''
        for card in hand:
            strr += card[0] + ' '
        return strr

    def valueOfHand(self, hand):
        total = 0
        for card in hand:
            total += card[1]
        return total