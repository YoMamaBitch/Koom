from datetime import datetime
import utility
from discord.ui import Button,View, Select
import discord
from discord import Interaction, SelectMenu, SelectOption, TextStyle, ui

class CoinflipView(View):
    def __init__(self, game_data, casinoCog):
        super().__init__()
        self.casinoCog = casinoCog
        self.game_data = game_data
        self.add_item(CoinflipButton(label='Join',emoji='<:doggin:911710984165539860>',row=0))

    async def callback(self, interaction:discord.Interaction):
        self.children[0].disabled = True
        embed = self.casinoCog.generateCoinflipStartEmbed(self.game_data)
        self.game_data['player2'] = interaction.user
        await self.game_data['followup'].edit_message(message_id=self.game_data['followupId'], embed=embed, view=self)
        modal = CoinflipModal(self)
        await interaction.response.send_modal(modal)
        await modal.wait()
        try:
            value = float(modal.answer.value)
            if value > self.game_data['higher'] or value < self.game_data['lower']:
                interaction.response.send_message("You didn't enter a value between the higher and lower.",ephemeral=True)
                raise
            elif not await utility.checkIfUserHasAmount(interaction.user.id, value):
                interaction.response.send_message("You don't have the amount needed to bet.",ephemeral=True)
                raise
        except:
            self.children[0].disabled = False
            await self.game_data['followup'].edit_message(message_id=self.game_data['followupId'], embed=embed, view=self)
            return       
        await utility.takeMoneyFromId(interaction.user.id, value)
        self.game_data['player2Bet'] = value
        await self.casinoCog.coinflipCallback(self,self.game_data)

    async def on_timeout(self) -> None:
        await self.casinoCog.coinflipTimeout(self.game_data)
        return await super().on_timeout()

    async def interaction_check(self, interaction: Interaction) -> bool:
        #if 'player2' in self.game_data:
        #    return interaction.user.id == self.game_data['player1'].id or interaction.user.id == self.game_data['player2'].id
        return interaction.user.id != self.game_data['player1'].id

class CoinflipButton(Button):
    def __init__(self, row = None, emoji=None, disabled = False, label='\u200b'):
        super().__init__(style=discord.ButtonStyle.green, label=label, row=row, emoji=emoji, disabled=disabled)
    
    async def callback(self, interaction: Interaction):
        return await self.view.callback(interaction)

class CoinflipModal(ui.Modal):
    answer = ui.TextInput(label='Your Amount', style=TextStyle.short, placeholder=f'Keep in mind you can only go between the lower and higher bounds.')
    def __init__(self,view) -> None:
        self.view = view
        lower = view.game_data['lower']
        higher = view.game_data['higher']
        self.answer.placeholder = f'Min: £{lower} Max: £{higher}'
        super().__init__(title="Join Coinflip", timeout=20)

    async def on_submit(self, interaction: Interaction) -> None:
        self.stop()
        await interaction.response.defer()
        await super().on_submit(interaction)
