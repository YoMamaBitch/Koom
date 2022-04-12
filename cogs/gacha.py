import discord,secrets, time, os, json, asyncio, utility, re
from random import Random
from challenge_view import ChallengeView
from discord.ext import commands
from discord import app_commands
from utility import *

ORIGINAL_SPAWN_CHANCE = 0.4

class Gacha(commands.Cog):
    def __init__(self,bot:commands.Bot)->None:
        self.bot = bot
        self.claimed = self.loadClaimedList()
        self.SPAWN_CHANCE = ORIGINAL_SPAWN_CHANCE
        self.SPAWN_INCREMENT = 0.08
        self.currentSpawn = None
        self.currentSpawnEmbed = None
        self.currentSpawnMessage = None
        with open('localGachaContent/uri.txt', 'r',encoding='utf-8') as f:
            self.skinURIs = f.readline().split(',')
        self.skinTiers = self.loadSkinTiers()
        self.activeTrades = []
        self.random = Random()
        self.spawnChannel = self.bot.get_partial_messageable(id=secrets.testGacha,type=discord.ChannelType.text)
        self.spawn_task = asyncio.get_event_loop().create_task(self.spawnSkins())
        self.lastClaimer = None
        self.lastClaimTime = 0

    @app_commands.command(name='challenge', description='Challenge the most recent skin claimer, incur a time penalty regardless of win/lose.')
    @app_commands.guilds(discord.Object(817238795966611466))
    async def challenge(self, interaction : discord.Interaction, user : discord.User)->None:
        id = interaction.user.id
        author = interaction.user.display_name
        url = interaction.user.display_avatar.url
        userid = user.id
        now = time.time()
        if now - self.lastClaimTime > 10:
            await interaction.response.send_message("10 seconds have elapsed.", ephemeral=True)
            return
        if self.lastClaimer == id or id == userid:
            await interaction.response.send_message("You can't challenge yourself.", ephemeral=True)
            return
        embed = self.generateChallengeEmbed(author,url,user.display_name)
        view = ChallengeView(id, user.id, self)
        await interaction.response.send_message(embed=embed,view=view)

    @commands.command()
    async def claim(self, ctx, *guess:str):
        fullGuess = ' '.join(guess)
        id = ctx.author.id
        if self.currentSpawn == None:
            await ctx.send("There is no currently spawned skin.")
            return
        self.ensureUserInDatabase(id)
        now = int(time.time())
        userdata = utility.cursor.execute('SELECT * FROM Gacha WHERE did IS ?',(id,)).fetchone()
        nextClaim = userdata[4]
        if nextClaim != 0 and nextClaim > now:
            timeLeftString = utility.secondsToMinSecString(int(nextClaim-now))
            await ctx.send(f"You can't claim for another {timeLeftString}")
            return
        inventory = userdata[3].split(',')
        if self.currentSpawn.lower() == fullGuess.lower():
            if len(inventory) == 250:
                await ctx.send(f"You don't have enough inventory spaces, {ctx.author.display_name}")
                return
            globalClaimedList = utility.cursor.execute('SELECT claimed FROM Gacha WHERE did IS 1').fetchone()[0]
            userClaimedList = utility.cursor.execute('SELECT claimed FROM Gacha WHERE did IS ?',(id,)).fetchone()[0]
            globalClaimedList += f',{self.currentSpawn}'
            userClaimedList += f'{self.currentSpawn},'
            self.claimed.append(self.currentSpawn)
            nextClaim = now + 3600
            utility.cursor.execute('UPDATE Gacha SET claimed = ? WHERE did IS 1',(globalClaimedList,))
            utility.cursor.execute('UPDATE Gacha SET claimed = ?, next_claim = ? WHERE did IS ?',(userClaimedList,nextClaim,id,))
            utility.database.commit()
            await self.sendClaimSuccessMessage(ctx)
            self.currentSpawn = None
            self.lastClaimer = ctx.author.id
            self.lastClaimTime = now
        else:
            await self.sendClaimFailedMessage(ctx)

    async def sendClaimFailedMessage(self,ctx):
        await ctx.message.add_reaction('<a:532214723437920276:963305339573399593>')

    async def sendClaimSuccessMessage(self, ctx):
        self.currentSpawnEmbed.set_footer(text=f'Claimed by {ctx.author.display_name}', icon_url=f'{ctx.author.display_avatar.url}')
        await self.currentSpawnMessage.edit(embed=self.currentSpawnEmbed)
        await ctx.message.add_reaction('<:952903594917646407:963305851483983873>')

    async def spawnSkins(self):
        while True:
            #randNum = self.random.random() * 100
            randNum = 0
            if randNum <= self.SPAWN_CHANCE:
                skinData = self.getRandomSkin()
                print(skinData)
                if skinData == None:
                    print("All skins collected")
                    return
                self.SPAWN_CHANCE = ORIGINAL_SPAWN_CHANCE
                await self.writeSpawnMessage(skinData)
            else:
                self.SPAWN_CHANCE += self.SPAWN_INCREMENT
            await asyncio.sleep(self.random.random() + 6)

    def generateChallengeEmbed(self, author, url, user)->discord.Embed:
        embed = discord.Embed(title=f'{user} has been challenged!',color=0xff030b, description="They have 30 minutes to respond before forfeiting the skin.")
        embed.set_author(name=f'{author}', icon_url=f'{url}')
        return embed        


    async def challengeViewCallback(self, view, interaction : discord.Interaction, challenger : tuple(int,str), challengee : tuple(int,str)):
        if challengee[1] == 'Accept':
            view.changeToChallengeChoice()
            embed = self.generateChallengeChoiceEmbed(challengee[0])
            await interaction.response.edit_message(embed=embed)
            return

    def generateChallengeChoiceEmbed(self, challengeeId):
        user = self.bot.get_user(challengeeId)
        embed = discord.Embed(title='Pick a challenge', color=0x471a7a)
        embed.set_author(name=f'{user.display_name}', icon_url=f'{user.display_avatar.url}')
        embed.add_field(name='1', value='```yaml\nMental Maths\n```', inline=False)
        embed.add_field(name='2', value='```yaml\nTyping\n```', inline=False)
        embed.add_field(name='3', value='```yaml\nTic-Tac-Toe\n```', inline=False)
        embed.add_field(name='4', value='```yaml\nRock Paper Scissors\n```', inline=False)
        return embed

    def getRandomSkin(self):
        startTime = time.time()
        endTime = startTime + 100
        while True:
            if time.time() > endTime:
                return None
            ticket = self.random.randint(0,46101)
            if ticket < 20000:
                skin = self.random.choice(self.skinTiers[0])
            elif ticket < 32000:
                skin =  self.random.choice(self.skinTiers[1])
            elif ticket < 40000:
                skin =  self.random.choice(self.skinTiers[2])
            elif ticket < 45000:
                skin =  self.random.choice(self.skinTiers[3])
            elif ticket < 46000:
                skin =  self.random.choice(self.skinTiers[4])
            elif ticket < 46100:
                skin =  self.random.choice(self.skinTiers[5])
            else:
                skin =  self.random.choice(self.skinTiers[6])
            if skin not in self.claimed:
                return skin

    async def writeSpawnMessage(self,skin):
        tier = self.getTierOfSkin(skin)
        self.currentSpawn = skin
        skin = self.convertSkinToUrl(skin)
        title = f'Tier {tier} Skin Spawned!'
        if tier == 1:
            color=0xbdbdbd
        elif tier==2:
            color=0x8ac5d4
        elif tier==3:
            color=0x68de7e
        elif tier==4:
            color=0xe2e835
        elif tier==5:
            color=0xf07d1f
        elif tier==6:
            color =0xf00e3b
        else:
            color=0xff00c3
        url = f'{secrets.skinBaseURL}{skin}'
        embed = discord.Embed(title=title, color=color, description="Claim using 'bruh claim \_\_\_\_\_\_'")
        embed.set_image(url=url)
        hidden_skin = self.convertUrlToHidden(skin)
        embed.add_field(name=f'{hidden_skin}', value='\u200b')
        self.currentSpawnEmbed = embed
        await self.sendMentionMessage()
        self.currentSpawnMessage = await self.spawnChannel.send(embed=embed)

    async def sendMentionMessage(self):
        user_data = utility.cursor.execute('SELECT * FROM Gacha').fetchall()
        wishlisters = []
        for x in user_data:
            if x[2] == self.currentSpawn:
                wishlisters.append(x[0])
        if len(wishlisters) == 0:
            return None
        msgContent = ''
        for x in wishlisters:
            msgContent += f'<@{x}> '
        msg = await self.spawnChannel.send(content=msgContent)
        await msg.delete(1.0)

    def convertUrlToHidden(self, skin):
        hiddenSkin = self.convertUrlToSkin(skin)
        hiddenSkin = re.sub('[A-Za-z0-9]','\_', hiddenSkin)
        return hiddenSkin

    def convertSkinToUrl(self, skin):
        return '_'.join(skin.split(' ')) + '.jpg'

    def convertUrlToSkin(self,url):
        return url.replace('_', ' ').replace('.jpg','').replace('%','/')

    def getTierOfSkin(self, skin):
        for x in range(0,len(self.skinTiers)):
            if skin in self.skinTiers[x]:
                return x+1

    def loadSkinTiers(self):
        with open('localGachaContent/rarities.txt', 'r', encoding='utf-8') as f:
            data = f.readline().split(',')
        t1,t2,t3,t4,t5,t6,t7 = [],[],[],[],[],[],[]
        for x in data:
            try:
                cost = int(x.split('+')[1])
                skin = x.split('+')[0]
            except:
                continue
            if cost >= 260 and cost <= 500:
                t1.append(skin)
            elif cost >= 520 and cost <=585:
                t2.append(skin)
            elif cost >= 750 and cost <= 880:
                t3.append(skin)
            elif cost == 975:
                t4.append(skin)
            elif cost >= 1350 and cost <= 2400:
                t5.append(skin)
            elif cost >= 2775 and cost <= 5000:
                t6.append(skin)
            else:
                t7.append(skin)
        return [t1,t2,t3,t4,t5,t6,t7]

    def loadClaimedList(self):
        data = utility.cursor.execute('SELECT claimed FROM Gacha WHERE did IS 1').fetchone()[0]
        return data.split(',')

    def ensureUserInDatabase(self,id):
        record = cursor.execute(f'SELECT * FROM Gacha WHERE did IS {id}').fetchone()
        if record == None:
            cursor.execute(f'''INSERT INTO Gacha VALUES ({id},?,?,?,?,?)''', ('','','',0,0))
            database.commit()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Gacha(bot))
