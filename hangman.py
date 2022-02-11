import discord
import asyncio
import motor.motor_asyncio
from bson.objectid import ObjectId
import secrets
import random
from cogs.utility import Utility

class HangmanGame():
    def __init__(self, bot, message, amount:int, otherPlayer):
        self.bot = bot
        self.amount = amount
        self.message = message
        self.messageChannel = message.channel
        self.outMsg = None
        self.hiddenWord = None
        self.fullWord = None
        self.player = message.author
        self.lives = 7
        
    async def start(self):
        await self.generateWord()
        await self.sendUpdate()

    async def generateWord(self):
        self.fullWord = "POOP"
        self.hiddenWord = "_ _ _ _" 
        return

    async def sendUpdate(self):
        name = self.player.display_name
        pp = self.player.avatar_url.BASE + self.player.avatar_url._url
        try:
            embed = discord.Embed(title="Hangman", description=f"{self.lives} lives remaining",color=0xb607de)
            embed.set_author(name=name,url=discord.Embed.Empty, icon_url=pp)
        except Exception as e:
            print(e)
        text = self.hiddenWord.replace('_','\_')
        embed.add_field(name="Word", value=text, inline=False)

        if (self.outMsg == None):
            self.outMsg = await self.message.channel.send(embed=embed)
            return
        await self.outMsg.edit(embed=embed)

    