from datetime import datetime
import difflib
import discord,secrets, time, asyncio, utility, re
from random import Random
from discord.ext import commands
from discord import ButtonStyle, Webhook, app_commands
from utility import *

ITEMS  = {'crisps':1, 'cola':1.5,'chocolate bar':2,'nuts':0.5,'sugar free nuts':0.35, 'koom bar':2, 'nesquik milkshake':2, 'oreos':2}

class Vending(commands.Cog):
    def __init__(self,bot:commands.Bot)->None:
        self.bot = bot

    @app_commands.command(name='consume', description="View the items you've bought from the vending machine.")
    #@app_commands.guilds(discord.Object(817238795966611466))
    async def consume(self, interaction : discord.Interaction, item:str):
        id = interaction.user.id
        item=item.lower()
        author = interaction.user.display_name
        icon = interaction.user.display_avatar.url
        self.ensureUserInDatabase(id)
        keys = list(ITEMS.keys())
        for x in range(0,len(keys)):
            if keys[x] == item:
                index = x
        utility.execute('SELECT * FROM Vending WHERE did = %s', (id,))
        inventory = utility.cursor.fetchone()
        if inventory[index+1] <= 0:
            await interaction.response.send_message("You can't consume something you have none of.", ephemeral=True)
            return
        value = inventory[index+1]
        value -= 1
        utility.execute(f'UPDATE Vending SET {item} = {value} WHERE did = %s', (id,))
        utility.commit()
        embed = self.generateConsumeEmbed(author,icon,item)
        await interaction.response.send_message(embed=embed)

    def generateConsumeEmbed (self, author,icon,item):
        embed = discord.Embed(title="It was delicious", color=0x22ff00, description=f"You have consumed {item}")
        embed.set_author(name=author,icon_url=icon)
        return embed

    @app_commands.command(name='pockets', description="View the items you've bought from the vending machine.")
    #@app_commands.guilds(discord.Object(817238795966611466))
    async def pockets(self, interaction : discord.Interaction):
        id = interaction.user.id
        author = interaction.user.display_name
        icon = interaction.user.display_avatar.url
        self.ensureUserInDatabase(id)
        utility.execute('SELECT * FROM Vending WHERE did = %s', (id,))
        inventory = utility.cursor.fetchone()
        embed =  self.generatePocketEmbed(author,icon, inventory)
        await interaction.response.send_message(embed=embed)

    def generatePocketEmbed(self, author, icon, inventory):
        embed = discord.Embed(title='Your Pockets', color=0x00fff2)
        embed.set_author(name=author, icon_url=icon)
        keys = list(ITEMS.keys())
        for index in range(1,len(inventory)):
            item = keys[index-1].title()
            embed.add_field(name=item,value=f'```yaml\n{inventory[index]}\n```')
        embed.set_footer(text="Consume items with /consume")
        return embed

    @app_commands.command(name='vending', description='Display the available products.')
    #@app_commands.guilds(discord.Object(817238795966611466))
    async def vending(self, interaction : discord.Interaction):
        keys = list(ITEMS.keys())
        embed = discord.Embed(title='Vending Machine', color=0xfcee21)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        desc = '```css\n'
        for key in keys:
            strValue = '{:.02f}'.format(float(ITEMS[key]))
            desc += f'[£{strValue}] {key.title()}\n'
        desc += '```'
        embed.add_field(name='Items', value=desc,inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='buyvending', description='Buy something from a vending machine.')
    #@app_commands.guilds(discord.Object(817238795966611466))
    async def buyvending(self, interaction : discord.Interaction, item : str):
        id = interaction.user.id
        author = interaction.user.display_name
        icon = interaction.user.display_avatar.url
        item = item.lower()
        if item.lower() not in ITEMS:
            await interaction.response.send_message("The vending machine doesn't stock that yet", ephemeral=True)
            return
        self.ensureUserInDatabase(id)
        if not await utility.checkIfUserHasAmount(id, ITEMS[item]):
            await interaction.response.send_message("You don't have enough money.", ephemeral=True)
            return
        await utility.takeMoneyFromId(id, ITEMS[item])
        utility.execute(f'SELECT {item} FROM Vending WHERE did = %s', (id,))
        amount = utility.cursor.fetchone()[0]
        amount += 1
        utility.execute(f'UPDATE Vending SET {item} = %s WHERE did = %s', (amount,id,))
        utility.commit()
        embed=self.generateBoughtEmbed(author,icon,item)
        await interaction.response.send_message(embed=embed)

    def generateBoughtEmbed(self, author, icon, item):
        embed = discord.Embed(title=f'Bought Item', color=0xfc0352, description=f"Bought {item} from the vending machine for £{ITEMS[item]}")
        embed.set_author(name=author, icon_url=icon)
        return embed

    def ensureUserInDatabase(self, id):
        utility.execute('SELECT * FROM Vending WHERE did = %s', (id,))
        entry = utility.cursor.fetchone()
        if entry is None:
            utility.execute(f'INSERT INTO Vending VALUES ({id},0,0,0,0,0,0,0,0)')
            utility.commit()

    @buyvending.autocomplete('item')
    async def coinflip_complete(self, interaction : discord.Interaction, current : str):
        return[
            app_commands.Choice(name=item, value=item)
            for item in ITEMS if current.lower() in item.lower()
        ]

    @consume.autocomplete('item')
    async def coinflip_complete(self, interaction : discord.Interaction, current : str):
        return[
            app_commands.Choice(name=item, value=item)
            for item in ITEMS if current.lower() in item.lower()
        ]

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Vending(bot))