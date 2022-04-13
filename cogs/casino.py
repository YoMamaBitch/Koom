import discord,secrets, utility, random, datetime, os
from PIL import Image, ImageDraw, ImageFont
from discord.ext import commands
from discord import app_commands
from blackjack_view import BlackjackView

class Casino(commands.Cog):
    def __init__(self,bot:commands.Bot)->None:
        self.bot = bot
        self.activeBJ = []

    @app_commands.command(name='blackjack', description="Start a blackjack game")
    #@app_commands.guilds(discord.Object(817238795966611466))
    async def blackjack(self, interaction:discord.Interaction, amount:app_commands.Range[float,1,50]):
        for x in self.activeBJ:
            if x['discord_id'] == interaction.user.id:
                await interaction.response.send_message("You're already in a Blackjack game.", ephemeral=True)
                return
        suits = ['diamonds','hearts','spades','clubs']
        deck = {}
        for i in suits:
            for j in range(1,14):
                cardname = f'{i}{j}.png'
                value = min(j,10)
                if j == 1:
                    value = 11
                deck[cardname] = value
        game_data = {'player':{}, 'dealer':{}, 'deck':deck, 'bet':amount, 'discord_id':interaction.user.id, 'discord_icon':interaction.user.avatar.url}
        self.hitHand(game_data['dealer'], deck)
        self.hitHand(game_data['player'], deck)
        self.hitHand(game_data['player'], deck)
        self.activeBJ.append(game_data)
        view = BlackjackView(game_data['discord_id'],self)
        await utility.takeMoneyFromId(game_data['discord_id'], amount)
        await utility.addBlackjackProfit(game_data['discord_id'], -amount)
        embed = await self.generateBlackJackEmbed(game_data)
        await interaction.response.send_message(embed=embed,view=view)

    async def blackjackViewCallback(self,interaction:discord.Interaction, did, label):
        notFound = True
        for x in self.activeBJ:
            if x['discord_id'] == did:
                game_data=x
                notFound = False
                break
        if notFound:
            return
        won = False
        draw = False
        if label == 'Hit':
            self.hitHand(game_data['player'], game_data['deck'])
            if self.getHandValue(game_data['player']) > 21:
                embed = await self.generateBlackJackEmbed(game_data)
                embed.set_author(name='Bust! You lose.')
                embed.set_footer(text=f"You lost £{game_data['bet']}")
                await interaction.response.edit_message(embed=embed)
                self.activeBJ.remove(game_data)
                return
            self.updateDealer(game_data['dealer'],game_data['deck'], False)
            if self.getHandValue(game_data['dealer']) > 21:
                embed = await self.generateBlackJackEmbed(game_data)
                embed.set_author(name='Dealer Bust! You Win!')
                embed.set_footer(text=f"You won £{game_data['bet'] * 2}")
                await interaction.response.edit_message(embed=embed)
                self.activeBJ.remove(game_data)
                won = True
        else:
            self.updateDealer(game_data['dealer'],game_data['deck'], True)
            embed = await self.generateBlackJackEmbed(game_data)
            if self.getHandValue(game_data['dealer']) > 21:
                embed.set_author(name='Dealer Bust! You Win!')
                embed.set_footer(text=f"You won £{game_data['bet'] * 2}")
                await interaction.response.edit_message(embed=embed)
                self.activeBJ.remove(game_data)
                won = True
            elif self.getHandValue(game_data['dealer']) > self.getHandValue(game_data['player']):
                embed.set_author(name='Dealer Drew Higher, You Lose.')
                embed.set_footer(text=f"You lost £{game_data['bet']}")
                await interaction.response.edit_message(embed=embed)
                self.activeBJ.remove(game_data)
                return
            elif self.getHandValue(game_data['player']) > self.getHandValue(game_data['dealer']):
                embed.set_author(name='You Drew Higher, You Win!')
                embed.set_footer(text=f"You won £{game_data['bet']}")
                await interaction.response.edit_message(embed=embed)
                self.activeBJ.remove(game_data)
                won = True
            elif len(game_data['dealer']) < len(game_data['player']):
                embed.set_author(name='Dealer Has Less Cards, You Lose.')
                embed.set_footer(text=f"You lost £{game_data['bet']}")
                await interaction.response.edit_message(embed=embed)
                self.activeBJ.remove(game_data)
                return
            elif len(game_data['player']) < len(game_data['dealer']):
                embed.set_author(name='You Have Less Cards, You Win!')
                embed.set_footer(text=f"You won £{game_data['bet'] * 2}")
                await interaction.response.edit_message(embed=embed)
                self.activeBJ.remove(game_data)
                won = True
            else:
                embed.set_author(name='Same Number of Cards and Same Value, You Draw.')
                embed.set_footer(text=f"Your bet has been refunded (£{game_data['bet']})")
                await interaction.response.edit_message(embed=embed)
                self.activeBJ.remove(game_data)
                draw = True
        if won:
            await utility.sendMoneyToId(game_data['discord_id'], game_data['bet'] * 2)
            await utility.addBlackjackProfit(game_data['discord_id'], game_data['bet'] * 2)
            return
        if draw:
            await utility.sendMoneyToId(game_data['discord_id'], game_data['bet'])
            await utility.addBlackjackProfit(game_data['discord_id'], game_data['bet'])
            return
        embed = await self.generateBlackJackEmbed(game_data)
        await interaction.response.edit_message(embed=embed)
        return
        
    async def generateBlackJackEmbed(self,game_data):
        embed= discord.Embed(title='Blackjack', color=0x14a307)
        playerHand = game_data['player']
        dealerHand = game_data['dealer']
        backImage = Image.open('localCasinoContent/board.png')
        draw = ImageDraw.Draw(backImage)
        font = ImageFont.truetype('localValorantContent/Cafe.ttf', 48)
        font2 = ImageFont.truetype('localValorantContent/Cafe.ttf', 24)
        draw.text((60,50), "YOU", (255,255,255), font=font, stroke_width=2, stroke_fill=(0,0,0))
        draw.text((275,50), "DEALER", (255,255,255), font=font, stroke_width=2, stroke_fill=(0,0,0))
        cardCount = 0
        width = 45
        size = 128
        if len(playerHand) > 4:
            diff = len(playerHand) - 4
            width -= (diff * 7)
            size -= (diff * 8)
        for cardKey in playerHand:
            valueOfHand = self.getHandValue(playerHand)
            card_image = Image.open(f'localCasinoContent/{cardKey}')
            card_image.thumbnail((size,size), Image.ANTIALIAS)
            backImage.paste(card_image, (15 + (cardCount*width), 165), card_image)
            draw.text((100,105), f"{valueOfHand}", (255,255,255), font=font2, stroke_width=1, stroke_fill=(0,0,0))
            cardCount+=1
        cardCount = 0
        size = 128
        width = 45
        if len(dealerHand) > 4:
            diff = len(dealerHand) - 4
            width -= (diff * 7)
            size -= (diff * 8)
        for cardKey in dealerHand:
            valueOfHand = self.getHandValue(dealerHand)
            card_image = Image.open(f'localCasinoContent/{cardKey}')
            card_image.thumbnail((size,size), Image.ANTIALIAS)
            backImage.paste(card_image, (260 + (cardCount*width), 165), card_image)
            draw.text((345,105), f"{valueOfHand}", (255,255,255), font=font2, stroke_width=1, stroke_fill=(0,0,0))
            cardCount+=1
        filepath = f"{datetime.datetime.now().strftime('%H-%M-%S')}.png"
        backImage.save(filepath)
        file = discord.File(filepath, filename='board.png')
        vKChannel = self.bot.get_channel(secrets.valImageChannel)
        img_msg = await vKChannel.send(file=file)
        embed.set_image(url=img_msg.attachments[0].url)
        os.remove(filepath)
        return embed

    def getHandValue(self,hand:dict):
        sum = 0
        aces = 0
        for key,value in hand.items():
            sum += value
            if value == 11:
                aces += 1
            if sum > 21:
                if aces > 0:
                    aces-=1
                    sum -= 10
        return sum

    def updateDealer(self, hand,deck, drawTil17):
        if drawTil17:
            while self.getHandValue(hand) < 17:
                self.hitHand(hand,deck)
            return
        self.hitHand(hand,deck)

    def hitHand(self, hand:list, deck:dict):
        card,value = random.choice(list(deck.items()))
        deck.pop(card)
        hand[card]=value

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Casino(bot))
