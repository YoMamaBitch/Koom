from discord.ui import Button,View, Select
import discord
from discord import Interaction, SelectMenu, SelectOption

class ValorantMatchView(View):
    def __init__(self, match_embed_data, valCog):
        super().__init__()
        round_index = match_embed_data['roundIndex']
        match_data = match_embed_data['matches'][round_index]
        self.match_embed_data = match_embed_data
        self.valCog = valCog
        self.addMatchListButtons()
        #self.add_item(ValRoundSelector(match_data['roundResults']))

    def enableMatch(self):
        self.clear_items()
        self.addRoundButtons()
        self.addBackButton()

    def enableRound(self):
        self.clear_items()
        self.addRoundButtons()
        self.addEventButtons()
        self.addBackButton()
        #self.children[6].disabled = False
        #self.children[7].disabled = False
        #self.children[8].disabled = False
        #self.children[11].disabled = False
        #self.children[12].disabled = False

    def enableOverview(self):
        self.clear_items()
        self.addMatchListButtons()
        # self.children[6].disabled = True
        # self.children[7].disabled = True
        # self.children[8].disabled = True
        #self.children[11].disabled = True
        #self.children[12].disabled = True

    def addBackButton(self):
        self.add_item(ValMatchButton(row=3,emoji='↪️'))

    def addEventButtons(self):
        self.add_item(ValMatchButton(row=1, emoji='⬅️', label='Prev Event')).add_item(ValMatchButton(row=1,emoji='➡️',label='Next Event'))

    def addRoundButtons(self):
        self.add_item(ValMatchButton(row=0, emoji='⬅️', label='Prev Round')).add_item(ValMatchButton(row=0,emoji='➡️',label='Next Round'))

    def addMatchListButtons(self):
        self.add_item(ValMatchButton(index=1,row=0)).add_item(ValMatchButton(index=2,row=0)).add_item(ValMatchButton(index=3,row=0))
        self.add_item(ValMatchButton(index=4,row=1)).add_item(ValMatchButton(index=5,row=1)).add_item(ValMatchButton(index=6,row=1))

    async def on_timeout(self) -> None:
        self.valCog.removeMatchList(self.match_embed_data)
        return await super().on_timeout()

    async def callback(self, interaction, index, emoji):
        await self.valCog.matchViewCallback(self, interaction, index, emoji)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.match_embed_data['id']

class ValMatchButton(Button):
    def __init__(self, index = -1, row = None, emoji=None, disabled = False, label='\u200b'):
        self.match_index = index
        if index == -1:
            super().__init__(style=discord.ButtonStyle.secondary,label=label, row=row, emoji=emoji, disabled=disabled)
        else:
            super().__init__(style=discord.ButtonStyle.secondary, label=index, row=row, emoji=emoji, disabled=disabled)
    
    async def callback(self, interaction: Interaction):
        return await self.view.callback(interaction, self.match_index, self.emoji)

class ValRoundSelector(Select):
    def __init__(self, roundData):
        super().__init__(placeholder="Skip to a round")

