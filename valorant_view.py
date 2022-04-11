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
        self.addBackButton()

    def enableOverview(self):
        self.clear_items()
        self.addMatchListButtons()
    
    def enableBackOnly(self):
        self.clear_items()
        self.addBackRoundButton()
        self.addBackButton()

    def addBackButton(self):
        self.add_item(ValMatchButton(row=3,emoji='↪️'))

    def addRoundButtons(self):
        self.addBackRoundButton().add_item(ValMatchButton(row=0,emoji='➡️',label='Next Round'))
        self.add_item(ValMatchButton(row=1, emoji='⬅️', label='Prev Event')).add_item(ValMatchButton(row=1,emoji='➡️',label='Next Event'))

    def addBackRoundButton(self):
        return self.add_item(ValMatchButton(row=0, emoji='⬅️', label='Prev Round'))

    def addMatchListButtons(self):
        self.add_item(ValMatchButton(label='1',row=0)).add_item(ValMatchButton(label='2',row=0)).add_item(ValMatchButton(label='3',row=0))
        self.add_item(ValMatchButton(label='4',row=1)).add_item(ValMatchButton(label='5',row=1)).add_item(ValMatchButton(label='6',row=1))
        self.add_item(ValMatchButton(row=0, emoji='⬅️', label='Prev')).add_item(ValMatchButton(row=0,emoji='➡️',label='Next'))

    async def on_timeout(self) -> None:
        self.valCog.removeMatchList(self.match_embed_data)
        return await super().on_timeout()

    async def callback(self, interaction, index, emoji):
        await self.valCog.matchViewCallback(self, interaction, index, emoji)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.match_embed_data['id']

class ValMatchButton(Button):
    def __init__(self, row = None, emoji=None, disabled = False, label='\u200b'):
        super().__init__(style=discord.ButtonStyle.secondary, label=label, row=row, emoji=emoji, disabled=disabled)
    
    async def callback(self, interaction: Interaction):
        return await self.view.callback(interaction, self.label, self.emoji)

class ValRoundSelector(Select):
    def __init__(self, roundData):
        super().__init__(placeholder="Skip to a round")

