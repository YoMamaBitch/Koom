from discord.ui import Button,View
import discord 
from discord import Interaction

class ValorantMatchView(View):
    def __init__(self, match_embed_data, valCog):
        super().__init__()
        self.match_embed_data = match_embed_data
        self.valCog = valCog
        self.add_item(ValMatchButton(index=1,row=0)).add_item(ValMatchButton(index=2,row=0)).add_item(ValMatchButton(index=3,row=0))
        self.add_item(ValMatchButton(row=0, emoji='⬅️')).add_item(ValMatchButton(row=0,emoji='➡️'))
        self.add_item(ValMatchButton(row=1,emoji='↪️', disabled=True))

    def disableNav(self):
        self.children[3].disabled = True
        self.children[4].disabled = True
        self.children[5].disabled = False

    def enableNav(self):
        self.children[3].disabled = False
        self.children[4].disabled = False
        self.children[5].disabled = True

    async def on_timeout(self) -> None:
        self.valCog.removeMatchList(self)
        return await super().on_timeout()

    async def callback(self, interaction, index, emoji):
        await self.valCog.matchViewCallback(self, interaction, index, emoji)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.match_embed_data[0]

class ValMatchButton(Button):
    def __init__(self, index = -1, row = -1, emoji=None, disabled = False):
        self.match_index = index
        if index == -1:
            super().__init__(style=discord.ButtonStyle.primary,label='\u200b', emoji=emoji, disabled=disabled)
        else:
            super().__init__(style=discord.ButtonStyle.secondary, label=index, row=row, emoji=emoji, disabled=disabled)
        
    
    async def callback(self, interaction: Interaction):
        return await self.view.callback(interaction, self.match_index, self.emoji)

