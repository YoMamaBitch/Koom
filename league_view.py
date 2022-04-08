from discord.ui import Button,View
import discord 
from discord import ButtonStyle, Interaction

class LeagueMatchView(View):
    def __init__(self, match_embed_data, leagueCog):
        super().__init__()
        self.match_embed_data = match_embed_data
        self.leagueCog = leagueCog
        self.add_item(LeagueMatchButton(index=1,row=0)).add_item(LeagueMatchButton(index=2,row=0)).add_item(LeagueMatchButton(index=3,row=0))
        self.add_item(LeagueMatchButton(index=4,row=1)).add_item(LeagueMatchButton(index=5,row=1)).add_item(LeagueMatchButton(index=6,row=1))
        self.add_item(LeagueMatchButton(index=7,row=2)).add_item(LeagueMatchButton(index=8,row=2)).add_item(LeagueMatchButton(index=9,row=2))
        self.add_item(LeagueMatchButton(row=0, emoji='⬅️')).add_item(LeagueMatchButton(row=0,emoji='➡️'))
    
    async def callback(self, interaction, index, emoji):
        await self.leagueCog.matchViewCallback(self, interaction, index, emoji)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.match_embed_data[0]

class LeagueMatchButton(Button):
    def __init__(self, index = -1, row = -1, emoji=None):
        self.match_index = index
        self.display_emoji = emoji
        if index == -1:
            super().__init__(style=discord.ButtonStyle.secondary,label='\u200b', emoji=emoji)
        else:
            super().__init__(style=discord.ButtonStyle.primary, label=index, row=row, emoji=emoji)
        
    
    async def callback(self, interaction: Interaction):
        return await self.view.callback(interaction, self.match_index, self.emoji)

