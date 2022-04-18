from discord.ui import Button,View, Select
import discord
from discord import Interaction, SelectMenu, SelectOption

class SellSkinView(View):
    def __init__(self, discord_id, gachaCog):
        super().__init__()
        self.gachaCog = gachaCog
        self.discord_id = discord_id
        self.add_item(SellSkinButton(label='Sell',emoji='<:rooSob:744345453923139714>',row=0)).add_item(SellSkinButton(label='Cancel',emoji='<:vv:597590298964656169>',row=0))

    async def callback(self, interaction, label):
        await self.gachaCog.sellSkinViewCallback(interaction, self.discord_id, label)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.discord_id

class SellSkinButton(Button):
    def __init__(self, row = None, emoji=None, disabled = False, label='\u200b'):
        super().__init__(style=discord.ButtonStyle.secondary, label=label, row=row, emoji=emoji, disabled=disabled)
    
    async def callback(self, interaction: Interaction):
        return await self.view.callback(interaction, self.label)
