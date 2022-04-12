from discord.ui import Button,View, Select
import discord
from discord import Interaction, SelectMenu, SelectOption

class BlackjackView(View):
    def __init__(self, discord_id, casinoCog):
        super().__init__()
        self.casinoCog = casinoCog
        self.discord_id = discord_id
        self.add_item(BlackjackButton(label='Hit',emoji='<:pwese:915016939523407873>',row=0)).add_item(BlackjackButton(label='Stand',emoji='<:8748_gigachad:963015025033904148>',row=0))

    async def callback(self, interaction, label):
        await self.casinoCog.blackjackViewCallback(interaction, self.discord_id, label)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.discord_id

class BlackjackButton(Button):
    def __init__(self, row = None, emoji=None, disabled = False, label='\u200b'):
        super().__init__(style=discord.ButtonStyle.secondary, label=label, row=row, emoji=emoji, disabled=disabled)
    
    async def callback(self, interaction: Interaction):
        return await self.view.callback(interaction, self.label)
