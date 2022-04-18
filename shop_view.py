from discord.ui import Button,View, Select
import discord
from discord import Interaction, SelectMenu, SelectOption

class ShopGachaView(View):
    def __init__(self, discord_id, gachaCog,skinList,canBuyList):
        super().__init__()
        self.gachaCog = gachaCog
        self.discord_id = discord_id
        self.skinList = skinList
        self.canBuy = canBuyList
        self.enableList()

    def enableList(self):
        self.clear_items()
        for i in range(0,len(self.canBuy)):
            if self.canBuy[i]:
                self.add_item(ShopGachaButton(label=f'{i+1}', disabled=False))
            else:
                self.add_item(ShopGachaButton(label=f'{i+1}', disabled=True))

    def enableBuy(self):
        self.clear_items()
        self.add_item(ShopGachaButton(label='Yes')).add_item(ShopGachaButton(label='Go back'))

    async def callback(self, interaction, label):
        if label.isdigit():
            self.activeSkin = int(label)-1
        await self.gachaCog.shopViewCallback(interaction, self, label)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.discord_id

class ShopGachaButton(Button):
    def __init__(self, row = None, emoji=None, disabled = False, label='\u200b'):
        super().__init__(style=discord.ButtonStyle.secondary, label=label, row=row, emoji=emoji, disabled=disabled)
    
    async def callback(self, interaction: Interaction):
        return await self.view.callback(interaction, self.label)
