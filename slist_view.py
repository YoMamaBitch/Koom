from discord.ui import Button,View, Select
import discord
from discord import ButtonStyle, Interaction, SelectMenu, SelectOption

class SlistView(View):
    def __init__(self,id, data, gachaCog):
        super().__init__()
        self.gachaCog = gachaCog
        self.userid = id
        self.data = data
        self.add_item(SlistButton(label='Prev')).add_item(SlistButton(label='Next'))

    async def callback(self, interaction, label):
        await self.gachaCog.slistCallback(self.data,interaction, label)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.userid
    
class SlistButton(Button):
    def __init__(self, row = 0,label=None, emoji=None, disabled = False):
        super().__init__(style=discord.ButtonStyle.secondary, label=label, row=row, emoji=emoji, disabled=disabled)
        
    
    async def callback(self, interaction: Interaction):
        return await self.view.callback(interaction, self.label)

