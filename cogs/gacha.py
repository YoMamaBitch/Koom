from datetime import datetime
import difflib
import discord,secrets, time, asyncio, utility, re
from random import Random
from sellskin_view import SellSkinView
from slist_view import SlistView
from shop_view import ShopGachaView
from trade_view import TradeView
from discord.ext import commands
from discord import ButtonStyle, Webhook, app_commands
from utility import *

ORIGINAL_SPAWN_CHANCE = 0.3
TIER_SELL_PRICE = [2.5,6,15,40,100,500,4000]
SHOP_PRICES = [250,750,1250,2500,5000]
SHOP_CHANCES = [4500,7000,8700,9700,10001]

class Gacha(commands.Cog):
    def __init__(self,bot:commands.Bot)->None:
        self.bot = bot
        self.claimed = self.loadClaimedList()
        self.SPAWN_CHANCE = ORIGINAL_SPAWN_CHANCE
        self.SPAWN_INCREMENT = 0.08
        self.currentSpawn = None
        self.currentSpawnEmbed = None
        self.currentSpawnMessage = None
        self.challengesEnabled = True
        with open('localGachaContent/uri.txt', 'r',encoding='utf-8') as f:
            self.skinURIs = f.readline().split(',')
        self.skinTiers = self.loadSkinTiers()
        self.activeTrades = []
        self.activeSells = []
        self.random = Random()
        self.spawnChannel = self.bot.get_partial_messageable(id=secrets.gachaSpawnChannel,type=discord.ChannelType.text)
        self.spawn_task = asyncio.get_event_loop().create_task(self.spawnSkins())
        self.shop_task = asyncio.get_event_loop().create_task(self.resetShop())
        self.lastClaimer = None
        self.lastClaimTime = 0

    async def resetShop(self):
        while True:
            refreshTime = utility.cursor.execute('SELECT refreshed WHERE did IS 1').fetchone()[0]
            if refreshTime > time.time():
                self.refillShop()
                channel = self.bot.get_channel(886389462769217536)
                await channel.send("Shop refilled")
                now = int(time.time())
                nextUpdate = now + 604800
                utility.cursor.execute('UPDATE GachaShop SET refreshed = 0')
                utility.cursor.execute('UPDATE GachaShop SET refreshed = ? WHERE did IS 1', (nextUpdate,))
                utility.database.commit()
            await asyncio.sleep(3600)
            
    @app_commands.command(name='shop', description="Browse your weekly shop, this can be refreshed once per week for £500.")
    @app_commands.guilds(discord.Object(817238795966611466))
    async def shop(self, interaction :discord.Interaction)->None:
        id = interaction.user.id
        self.ensureUserInDatabase(id)
        self.updateShoppers()
        thisShopper = utility.cursor.execute('SELECT * FROM GachaShop WHERE did IS ?',(id,)).fetchone()
        if thisShopper[1] == '' or thisShopper[1] == None:
            self.fillShopForID(id)
            utility.database.commit()
        embed = discord.Embed(title='Shop', color=0x0ff207)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        currentShop = thisShopper[1].split(',')
        canBuy = []
        for skin in currentShop:
            money = await utility.getUserEconomy(id)
            money = money[1]
            tierOfSkin = self.getTierOfSkin(skin)
            emoji = '✅' if money >= SHOP_PRICES[tierOfSkin-1] else '❌'
            if emoji == '✅':
                canBuy.append(True)
            else:
                canBuy.append(False)
            embed.add_field(name=f'{skin} {emoji}',value=f'```yaml\n£{SHOP_PRICES[tierOfSkin-1]}\n```',inline=False)
        view = ShopGachaView(id, self, currentShop, canBuy)
        await interaction.response.send_message(embed=embed, view=view)

    async def shopViewCallback(self, interaction:discord.Interaction, view : ShopGachaView, label:str):
        if label.isdigit():
            view.enableBuy()
            skin = view.skinList[int(label)-1]
            embed = discord.Embed(title=f'Buy {skin}', color=0x55ff00)
            skinImage = self.convertSkinToUrl(skin)
            embed.set_image(url=f'{secrets.skinBaseURL}{skinImage}')
            tier = self.getTierOfSkin(skin)
            embed.add_field(name='Cost',value=f'```yaml\n£{SHOP_PRICES[tier-1]}\n```')
            await interaction.response.edit_message(embed=embed,view=view)
            return
        elif label == 'Go back':
            view.enableBuy()
            await interaction.response.edit_message(view=view)
            return
        elif label == 'Yes':
            view.clear_items()
            skin = view.skinList[view.activeSkin]
            globalClaimList = utility.cursor.execute('SELECT claimed FROM Gacha WHERE did IS 1').fetchone()[0]
            if skin in globalClaimList:
                embed=discord.Embed(title='Error',color=0xd91709)
                embed.add_field(name='\u200b',value='```\nThe skin in your shop has already been claimed.\n```')
                await interaction.response.edit_message(embed=embed,view=view)
                return
            tier = self.getTierOfSkin(skin)
            price = SHOP_PRICES[tier-1] 
            globalClaimList += f',{skin}'
            userClaimList = utility.cursor.execute('SELECT claimed FROM Gacha WHERE did IS ?', (interaction.user.id,)).fetchone()[0]
            userClaimList += f',{skin}'
            utility.cursor.execute('UPDATE Gacha SET claimed = ? WHERE did IS 1',(globalClaimList,))
            utility.cursor.execute('UPDATE Gacha SET claimed = ? WHERE did IS ?',(userClaimList,interaction.user.id,))
            await utility.takeMoneyFromId(interaction.user.id, price)
            embed = discord.Embed(title='Success', color=0x00ff15)
            embed.add_field(name=f'Bought {skin} for £{price}', value='\u200b')
            skinImage = self.convertSkinToUrl(skin)
            embed.set_image(url=f'{secrets.skinBaseURL}{skinImage}')
            await interaction.response.edit_message(embed=embed,view=view)

    def refillShop(self):
        self.updateShoppers()
        shoppers = utility.cursor.execute('SELECT * FROM GachaShop').fetchall()
        for shopper in shoppers:
            if shopper[0] == 1:
                continue
            self.fillShopForID(shopper[0])
        utility.database.commit()
            
    def fillShopForID(self, id ):
        nextShop = ''
        globalClaimList = utility.cursor.execute('SELECT claimed FROM Gacha WHERE did IS 1').fetchone()[0]
        for _ in range(0,4):
            while True:         
                success =False           
                ticket = self.random.randint(0,10000)
                for chance in range(0,len(SHOP_CHANCES)):
                    if ticket < SHOP_CHANCES[chance]:
                        skin = self.random.choice(self.skinTiers[chance])
                        if skin not in globalClaimList:
                            success = True
                        else:
                            break
                        nextShop += skin + ','
                        break
                if success:
                    break
        nextShop = nextShop.removesuffix(',')
        utility.cursor.execute('UPDATE GachaShop SET shop = ? WHERE did IS ?', (nextShop, id,))

    def updateShoppers(self):
        gachaUsers = utility.cursor.execute('SELECT * FROM Gacha').fetchall()
        shopUsers = utility.cursor.execute('SELECT * FROM GachaShop').fetchall()
        for user in gachaUsers:
            found=False
            for shopper in shopUsers:
                if shopper[0] == int(user[0]):
                    found = True
                    break
            if not found:
                utility.cursor.execute('INSERT INTO GachaShop VALUES(?,"", 0)', (user[0],))
        utility.database.commit()

    @app_commands.command(name='sellskin', description="Release a skin and get paid its worth.")
    #@app_commands.guilds(discord.Object(817238795966611466))
    async def sellskin(self, interaction :discord.Interaction, skinname:str)->None:
        id = interaction.user.id
        self.ensureUserInDatabase(id)
        userdata = utility.cursor.execute('SELECT * FROM Gacha WHERE did IS ?',(id,)).fetchone()
        claimed = userdata[3].split(',')
        closest_skin = difflib.get_close_matches(skinname, claimed, n=1, cutoff=0.25)[0]
        if closest_skin == None:
            await interaction.response.send_message("Couldn't find that skin in your claim list.",ephemeral=True)
            return
        self.activeSells.append([interaction.user.id,claimed,closest_skin])
        view = SellSkinView(interaction.user.id, self)
        embed= discord.Embed(title='Sell Skin',color=0x8a0dde)
        embed.add_field(name='Skin', value=f'```ini\n[{closest_skin}]\n```')
        embed.set_author(name=f'{interaction.user.display_name}', icon_url=f'{interaction.user.display_avatar.url}')
        value = TIER_SELL_PRICE[self.getTierOfSkin(closest_skin)-1]
        embed.add_field(name='Price', value=f'```diff\n+£{value}\n```')
        image_url = self.convertSkinToUrl(closest_skin)
        embed.set_image(url=f'{secrets.skinBaseURL}{image_url}')
        await interaction.response.send_message(embed=embed,view=view)
    
    async def sellSkinViewCallback(self,interaction, discord_id,label):
        game = None
        for x in self.activeSells:
            if x[0] == discord_id:
                game = x
        if game == None:
            return
        if label == 'Sell':
            x[1].remove(x[2])
            value = TIER_SELL_PRICE[self.getTierOfSkin(x[2])-1]
            totalClaimed = utility.cursor.execute('SELECT claimed FROM Gacha WHERE did IS 1').fetchone()[0]
            totalClaimedList = totalClaimed.split(',')
            totalClaimedList.remove(x[2])
            totalClaimed = ','.join(totalClaimedList)
            userClaimed = ','.join(x[1])
            utility.cursor.execute('UPDATE Gacha SET claimed = ? WHERE did IS 1', (totalClaimed,))
            utility.cursor.execute('UPDATE Gacha SET claimed = ? WHERE did IS ?', (userClaimed,x[0],))
            await utility.sendMoneyToId(x[0], value)
            embed = discord.Embed(title='Successfully Sold', color=0x20e842)
            embed.add_field(name='Turnover', value=f'```diff\n+£{value}\n```')
            image_url = self.convertSkinToUrl(x[2])
            embed.set_image(url=f'{secrets.skinBaseURL}{image_url}')
            await interaction.response.edit_message(embed=embed)
        else:
            embed = discord.Embed(title='Cancelled', color=0xe82a20)
            await interaction.response.edit_message(embed=embed)
        self.activeSells.remove(x)

    @app_commands.command(name='traderemove', description="Remove a skin from your active trade.")
    #@app_commands.guilds(discord.Object(817238795966611466))
    async def traderemove(self, interaction :discord.Interaction, skinname:str)->None:
        id = interaction.user.id
        trade = None
        for x in self.activeTrades:
            if x['sender'].id == id:
                key = 'senderOfferings'
                trade = x
                break
            elif x['recipient'].id == id:
                key = 'recipientOfferings'
                trade = x
                break
        if trade == None:
            await interaction.response.send_message("You aren't in an active trade.", ephemeral=True)
            return
        claimed = utility.cursor.execute('SELECT claimed FROM Gacha WHERE did IS ?',(id,)).fetchone()[0]
        claimed = claimed.split(',')
        closest_skin = difflib.get_close_matches(skinname, claimed, n=1,cutoff=0.3)[0]
        if closest_skin == None:
            await interaction.response.send_message("Couldn't find a skin similar to your search in your inventory.",ephemeral=True)
            return
        trade[key].remove(closest_skin)
        await interaction.response.send_message(f"Removed {closest_skin} from the trade.", ephemeral=True)
        embed =  self.generateTradeEmbed(x)
        followup : Webhook = x['followup']
        await followup.edit_message(message_id=x['followupId'],embed=embed)

    @app_commands.command(name='tradeadd', description="Add a skin to your active trade.")
    #@app_commands.guilds(discord.Object(817238795966611466))
    async def tradeadd(self, interaction :discord.Interaction, skinname:str)->None:
        id = interaction.user.id
        trade = None
        for x in self.activeTrades:
            if x['sender'].id == id:
                key = 'senderOfferings'
                trade = x
                break
            elif x['recipient'].id == id:
                key = 'recipientOfferings'
                trade = x
                break
        if trade == None:
            await interaction.response.send_message("You aren't in an active trade.", ephemeral=True)
            return
        claimed = utility.cursor.execute('SELECT claimed FROM Gacha WHERE did IS ?',(id,)).fetchone()[0]
        claimed = claimed.split(',')
        closest_skin = difflib.get_close_matches(skinname, claimed, n=1,cutoff=0.3)[0]
        if closest_skin == None:
            await interaction.response.send_message("Couldn't find a skin similar to your search in your inventory.",ephemeral=True)
            return
        trade[key].append(closest_skin)
    
        interaction.followup.auth_token
        await interaction.response.send_message(f"Added {closest_skin} to the trade.", ephemeral=True)
        embed =  self.generateTradeEmbed(x)
        followup : Webhook = x['followup']
        await followup.edit_message(message_id=x['followupId'],embed=embed)

    @app_commands.command(name='trade', description="Trade skins with a player.")
   # @app_commands.guilds(discord.Object(817238795966611466))
    async def trade(self, interaction :discord.Interaction, user:discord.User)->None:
        id = interaction.user.id
        cancelTrade = False
        if user.id == interaction.user.id:
            await interaction.response.send_message("Can't trade with yourself.",ephemeral=True)
            return
        for x in self.activeTrades:
            if x['sender'].id == id or x['sender'].id == user.id or x['recipient'].id == id or x['recipient'].id ==user.id:
                cancelTrade = True
                break
        if cancelTrade:
            await interaction.response.send_message("Someone is already in a trade.",ephemeral=True)
            return
        self.ensureUserInDatabase(id)
        self.ensureUserInDatabase(user.id)
        name = interaction.user.display_name
        url = interaction.user.display_avatar.url
        embed = self.generateTradeReqEmbed(name,url,user.display_name)
        data = {'sender':interaction.user, 'recipient':user, 'senderOfferings':[], 'recipientOfferings':[], 
        'senderAgreed':True,'recipientAgreed':False,'followup':interaction.followup}
        view = TradeView(id,data,self)
        await interaction.response.send_message(embed=embed,view=view)
        msg = await interaction.original_message()
        data['followupId'] = msg.id

    async def tradeCallback(self, view : TradeView,interaction:discord.Interaction,label):
        data = view.data
        if label == 'Accept':
            view.changeToTradeView()
            self.activeTrades.append(data)
            embed = self.generateTradeEmbed(data)
            await interaction.response.edit_message(embed=embed,view=view)
            return
        elif label == 'Reject':
            embed= self.generateRejectedTradeEmbed(data,interaction.user.id)
            view.disable()
            await interaction.response.edit_message(embed=embed,view=view)
            return
        elif label == 'Continue':
            if data['senderAgreed'] and data['recipientAgreed']:
                view.disable()
                await self.doTrade(data, interaction,view)
                self.activeTrades.remove(data)
            else:
                await self.editTradeAccepted(data,interaction,view)
            return
        elif label == 'Cancel':
            self.activeTrades.remove(data)
            view.disable()
            embed = self.generateRejectedTradeEmbed(data,interaction.user.id)
            await interaction.response.edit_message(embed=embed,view=view)
    
    async def editTradeAccepted(self,data,interaction,view):
        embed = self.generateTradeEmbed(data)
        embed.set_footer(text=f'Accepted by {interaction.user.display_name}')
        await interaction.response.edit_message(embed=embed,view=view)

    async def doTrade(self, data, interaction,view):
        senderId = data['sender'].id
        recId = data['recipient'].id
        senderName = data['sender'].display_name
        recName = data['recipient'].display_name
        senderList = data['senderOfferings']
        recList = data['recipientOfferings']
        databaseSender = utility.cursor.execute('SELECT claimed,favourite FROM Gacha WHERE did IS ?',(senderId,)).fetchone()
        databaseRecipient = utility.cursor.execute('SELECT claimed,favourite FROM Gacha WHERE did IS ?',(recId,)).fetchone()
        senderFav = databaseSender[1]
        recFav = databaseRecipient[1]
        databaseSender = databaseSender[0].split(',')
        databaseRecipient = databaseRecipient[0].split(',')
        sendBody = '```yaml\n '
        recBody = '```yaml\n '
        if senderFav in senderList:
            senderFav = ''
        if recFav in recList:
            recFav = ''
        for x in senderList:
            databaseRecipient.append(x)
            databaseSender.remove(x)
            sendBody += x + '\n '
        for x in recList:
            databaseSender.append(x)
            databaseRecipient.remove(x)
            recBody += x + '\n '
        sendBody += '\n```'
        recBody += '\n```'
        senderReturn = ','.join(databaseSender).removesuffix(',')
        recipientReturn = ','.join(databaseRecipient).removesuffix(',')
        utility.cursor.execute('UPDATE Gacha SET claimed = ?, favourite = ? WHERE did IS ?', (senderReturn,senderFav,senderId,))
        utility.cursor.execute('UPDATE Gacha SET claimed = ?, favourite = ? WHERE did IS ?', (recipientReturn,recFav,recId,))
        utility.database.commit()
        embed = discord.Embed(title='Trade Complete',color=0x08c21d, timestamp=datetime.now())
        embed.add_field(name=f'{senderName} Sent', value=sendBody)
        embed.add_field(name='\u200b', value='\u200b')
        embed.add_field(name=f'{recName} Sent', value=recBody)
        await interaction.response.edit_message(embed=embed,view=view)

    def generateRejectedTradeEmbed(self,data, cancelee):
        if cancelee == data['sender'].id:
            canceleeName = data['sender'].display_name
        else:
            canceleeName = data['recipient'].display_name
        embed = discord.Embed(title='Trade Cancelled', color=0xeb2315)
        embed.set_footer(text=f'Cancelled by {canceleeName}')
        return embed

    def generateTradeEmbed(self,data):
        embed= discord.Embed(title='Trade',color=0xe81ec6)
        senderName = data['sender'].display_name
        recipientName = data['recipient'].display_name
        senderList = data['senderOfferings']
        recipientList = data['recipientOfferings']
        senderBody = '```yaml\n '
        recipientBody = '```yaml\n '
        for x in senderList:
            senderBody += f'{x}\n'
        senderBody+='\n```'
        for x in recipientList:
            recipientBody += f'{x}\n'
        recipientBody += '\n```'
        embed.add_field(name=f"{senderName}'s Offerings",value=senderBody)
        embed.add_field(name='\u200b',value='\u200b')
        embed.add_field(name=f"{recipientName}'s Offerings",value=recipientBody)
        return embed

    def generateTradeReqEmbed(self, senderName, senderUrl, recipientName):
        embed= discord.Embed(title='Trade Offer', color=0x21bceb)
        embed.set_author(name=senderName, icon_url=senderUrl)
        embed.add_field(name='Recipient',value=recipientName)
        return embed

    @app_commands.command(name='slist', description="View your acquired skins.")
    #@app_commands.guilds(discord.Object(817238795966611466))
    async def slist(self, interaction :discord.Interaction)->None:
        id = interaction.user.id
        self.ensureUserInDatabase(id)
        userdata = utility.cursor.execute('SELECT * FROM Gacha WHERE did IS ?',(id,)).fetchone()
        data = {'fav':userdata[1], 'claimed':userdata[3], 'start':0, 'stop':10, 'name':interaction.user.display_name, 'icon':interaction.user.display_avatar.url}
        embed = self.generateSlistEmbed(data)
        view = SlistView(id, data,self)
        await interaction.response.send_message(embed=embed,view=view)

    @app_commands.command(name='favourite', description="Favourite a skin to display on your slist.")
    #@app_commands.guilds(discord.Object(817238795966611466))
    async def favourite(self, interaction :discord.Interaction, skin:str)->None:
        id = interaction.user.id
        self.ensureUserInDatabase(id)
        userdata = utility.cursor.execute('SELECT * FROM Gacha WHERE did IS ?',(id,)).fetchone()
        claimed = userdata[3].split(',')
        closest_skin = difflib.get_close_matches(skin, claimed, n=1, cutoff=0.3)
        if (len(closest_skin) == 0):
            await interaction.response.send_message("Couldn't find a skin close enough to your request.", ephemeral=True)
            return
        closest_skin = closest_skin[0]
        utility.cursor.execute('UPDATE Gacha SET favourite = ? WHERE did IS ?', (closest_skin, id,))
        utility.database.commit()
        embed = discord.Embed(title=f'Favourited {closest_skin}',color=0x3091f2)
        skinurl = self.convertSkinToUrl(closest_skin)
        embed.set_image(url=f'{secrets.skinBaseURL}{skinurl}')
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name='wl',description='Display your wishlisted skin.')
    #@app_commands.guilds(discord.Object(817238795966611466))
    async def wl(self, interaction :discord.Interaction)->None:
        id = interaction.user.id
        self.ensureUserInDatabase(id)
        userdata = utility.cursor.execute('SELECT * FROM Gacha WHERE did IS ?',(id,)).fetchone()
        if userdata[2] == '' or userdata[2] == None:
            await interaction.response.send_message("You don't have a wishlisted skin.",ephemeral=True)
            return
        url = self.convertSkinToUrl(userdata[2])
        embed = discord.Embed(title=f"{userdata[2]}", color=0xdb256e)
        embed.set_author(name=f'{interaction.user.display_name}', icon_url=f'{interaction.user.display_avatar.url}')
        embed.set_image(url=f'{secrets.skinBaseURL}{url}')
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='wishlistdel',description='Remove your wishlisted skin.')
   # @app_commands.guilds(discord.Object(817238795966611466))
    async def wishlistdel(self, interaction :discord.Interaction)->None:
        id = interaction.user.id
        self.ensureUserInDatabase(id)
        userdata = utility.cursor.execute('SELECT * FROM Gacha WHERE did IS ?',(id,)).fetchone()
        if userdata[2] == '' or userdata[2] == None:
            await interaction.response.send_message("You don't have a wishlisted skin.",ephemeral=True)
            return
        utility.cursor.execute('UPDATE Gacha SET wishlist = ? WHERE did IS ?',('',id,))
        utility.database.commit()
        embed = discord.Embed(title='Successfully Removed', color=0xd45613)
        embed.set_author(name=f'{interaction.user.display_name}', icon_url=f'{interaction.user.display_avatar.url}')
        embed.add_field(value=f'Removed {userdata[2]} from your wishlist. <:pepehands:690235036397731990>',name='\u200b')
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='wishlistadd',description='Add a skin to your wishlist. (Max 1)')
    #@app_commands.guilds(discord.Object(817238795966611466))
    async def wishlistadd(self, interaction :discord.Interaction, skin : str)->None:
        id = interaction.user.id
        self.ensureUserInDatabase(id)
        userdata = utility.cursor.execute('SELECT * FROM Gacha WHERE did IS ?',(id,)).fetchone()
        if userdata[2] != '' and userdata[2] != None:
            await interaction.response.send_message("You can't have more than 1 wishlisted skin.",ephemeral=True)
            return
        closest_skin = difflib.get_close_matches(skin,self.skinURIs, n=1,cutoff=0.3)
        if (len(closest_skin) == 0):
            await interaction.response.send_message("Couldn't find a skin close enough to your request.", ephemeral=True)
            return
        closest_skin = self.convertUrlToSkin(closest_skin[0])
        utility.cursor.execute('UPDATE Gacha SET wishlist = ? WHERE did IS ?',(closest_skin,id,))
        utility.database.commit()
        embed = discord.Embed(title='Successfully Added', color=0x15a146)
        embed.set_author(name=f'{interaction.user.display_name}', icon_url=f'{interaction.user.display_avatar.url}')
        embed.add_field(value=f'Added {closest_skin} to your wishlist. <:catOK:878977243278372885>',name='\u200b')
        await interaction.response.send_message(embed=embed)

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
            userClaimedList += f',{self.currentSpawn}'
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

    async def slistCallback(self,data, interaction :discord.Interaction,label):
        if label == 'Prev':
            if data['start'] == 0:
                return
            data['start'] -= 10
            data['stop'] -= 10
        elif label == 'Next':
            if data['stop'] >= len(data['claimed'].split(',')):
                return
            data['start'] += 10
            data['stop'] += 10
        embed = self.generateSlistEmbed(data)
        await interaction.response.edit_message(embed=embed)

    def generateSlistEmbed(self,data):
        favourite = self.convertSkinToUrl(data['fav'])
        skins = data['claimed'].split(',')
        if favourite == '.jpg':
            favourite = 'lol.png'
        favourite = f"{secrets.squareBaseUrl}{favourite}"
        body = '```ini\n'
        for i in range(data['start'],data['stop']):
            if i >= len(skins):
                break
            body += f'[{i+1}] {skins[i]}\n'
        body+='```'
        embed = discord.Embed(title='Skin List', color=0xe66f0e)
        embed.set_author(name=data['name'], icon_url=data['icon'])
        embed.add_field(name='\u200b',value=body,inline=False)
        embed.add_field(name='Total Skins',value=f'```yaml\n{len(skins)}\n```',inline=False)
        embed.set_thumbnail(url=favourite)
        return embed

    async def spawnSkins(self):
        while True:
            randNum = self.random.random() * 100
            #randNum = 0
            if randNum < self.SPAWN_CHANCE:
                skinData = self.getRandomSkin()
                print(skinData)
                if skinData == None:
                    print("All skins collected")
                    return
                self.SPAWN_CHANCE = ORIGINAL_SPAWN_CHANCE
                await self.writeSpawnMessage(skinData)
            else:
                self.SPAWN_CHANCE += self.SPAWN_INCREMENT
            await asyncio.sleep(self.random.random() * 55 + 35)

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
