from discord.ui import Button,View, Select
import discord
from discord import ButtonStyle, Interaction, SelectMenu, SelectOption

class TradeView(View):
    def __init__(self,id, data, gachaCog):
        super().__init__()
        self.gachaCog = gachaCog
        self.data = data
        self.isRequest = True
        self.add_item(TradeButton(label='Reject',emoji='<:among_us_dead:784255946326671372>'))
        self.add_item(TradeButton(label='Accept',emoji='<a:amongusdancing:911697659172098099>'))

    def disable(self):
        self.clear_items()

    def changeToTradeView(self):
        self.clear_items()
        self.isRequest = False
        self.data['senderAgreed'] = False
        self.data['recipientAgreed'] = False
        self.add_item(TradeButton(label='Cancel',emoji='<:blobban:759935431847968788>'))
        self.add_item(TradeButton(label='Continue',emoji='<:pepeOK:952903594917646407>'))

    async def callback(self, interaction, label):
        if label == 'Continue':
            if interaction.user.id == self.data['sender'].id:
                self.data['senderAgreed'] = True
            else:
                self.data['recipientAgreed'] = True
        await self.gachaCog.tradeCallback(self,interaction, label)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if self.isRequest:
            return interaction.user.id == self.data['recipient'].id
        return interaction.user.id == self.data['sender'].id or interaction.user.id == self.data['recipient'].id
    
class TradeButton(Button):
    def __init__(self, row = 0,label=None, emoji=None, disabled = False):
        super().__init__(style=discord.ButtonStyle.secondary, label=label, row=row, emoji=emoji, disabled=disabled)
    
    async def callback(self, interaction: Interaction):
        return await self.view.callback(interaction, self.label)

