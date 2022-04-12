from discord.ui import Button,View, Select
import discord
from discord import Interaction, SelectMenu, SelectOption

class ChallengeView(View):
    def __init__(self, challenger, challengee, gachaCog):
        super().__init__()
        #self.casinoCog = casinoCog
        self.gachaCog = gachaCog
        self.challengerId = challenger
        self.challengeeId = challengee
        self.challengerResponse = True
        self.challengeeResponse = False
        self.challengerChoice = ''
        self.challengeeChoice = ''
        style = discord.ButtonStyle.gray
        self.add_item(Button(style=style, label='Accept', emoji='✅'))
        #self.add_item(BlackjackButton(label='Hit',emoji='<:pwese:915016939523407873>',row=0)).add_item(BlackjackButton(label='Stand',emoji='<:8748_gigachad:963015025033904148>',row=0))

    async def callback(self, interaction, label):
        if interaction.user.id == self.challengeeId and self.challengeeChoice == label:
            self.challengeeResponse = False
            self.challengeeChoice = ''
        elif interaction.user.id == self.challengeeId:
            self.challengeeResponse = True
            self.challengeeChoice = label

        if interaction.user.id == self.challengerId and self.challengerChoice == label:
            self.challengerResponse = False
            self.challengerChoice = ''
        elif interaction.user.id == self.challengerId:
            self.challengerResponse = True
            self.challengerChoice = label

        if self.challengerResponse and self.challengeeResponse:
            await self.gachaCog.challengeViewCallback(self, interaction, (self.challengerId, self.challengerChoice),
                                    (self.challengeeId, self.challengeeChoice))
        self.challengeeResponse = False
        self.challengerResponse = False

    async def interaction_check(self, interaction: Interaction) -> bool:
        if len(self.children) == 1:
            return interaction.user.id == self.challengeeId
        return interaction.user.id == self.challengeeId or interaction.user.id == self.challengerId