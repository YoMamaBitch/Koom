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
        self.add_item(LeagueMatchButton(row=1,emoji='↪️', disabled=True))

    def disableNav(self):
        self.children[9].disabled = True
        self.children[10].disabled = True
        self.children[11].disabled = False

    def enableNav(self):
        self.children[9].disabled = False
        self.children[10].disabled = False
        self.children[11].disabled = True

    async def on_timeout(self) -> None:
        self.leagueCog.removeMatchList(self)
        return await super().on_timeout()

    async def callback(self, interaction, index, emoji):
        await self.leagueCog.matchViewCallback(self, interaction, index, emoji)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.match_embed_data[0]

class LeagueMatchButton(Button):
    def __init__(self, index = -1, row = -1, emoji=None, disabled = False):
        self.match_index = index
        if index == -1:
            super().__init__(style=discord.ButtonStyle.primary,label='\u200b', emoji=emoji, disabled=disabled)
        else:
            super().__init__(style=discord.ButtonStyle.secondary, label=index, row=row, emoji=emoji, disabled=disabled)
        
    
    async def callback(self, interaction: Interaction):
        return await self.view.callback(interaction, self.match_index, self.emoji)

