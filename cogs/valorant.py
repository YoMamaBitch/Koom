import json
from threading import local
import discord,secrets, utility, urllib.request
from riotwatcher import ValWatcher
from discord.ext import commands
from discord import app_commands

class Valorant(commands.Cog):
    def __init__(self,bot:commands.Bot)->None:
        self.bot = bot 
        self.watcher = ValWatcher(secrets.valKey)
        self.initialiseContent()
        self.initialiseMaps()

    @commands.command(name='pullcontent')
    async def pullcontent(self, ctx):
        if ctx.author.id != secrets.keironID:
            return
        try:
            content = self.watcher.content.contents('NA','en-GB')
        except:
            await ctx.send("Content server offline, try later bro")
            return
        self.content = content
        self.loadAbilities()
        self.saveJson('localValorantContent/content.json', self.content)
        await ctx.send("Updated successfully.")

    def checkContentForAbilities(self):
        if self.content['characters'][0].get('abilities') == None:
            self.loadAbilities()
            self.saveJson('localValorantContent/content.json', self.content)

    def saveJson(self, path, json):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(json))

    def loadAbilities(self):
        url = 'https://valorant-api.com/v1/agents/'
        for x in self.content['characters']:
            id = x['id']
            if id == '36FB82AF-409D-C0ED-4B49-57B1EB08FBD5':
                continue # Null UI Data exists...
            with urllib.request.urlopen(f'{url}{id}') as f:
                data = json.loads(f.read().decode('utf-8'))
            x['abilities'] = data['data']['abilities']

    def initialiseContent(self):
        with open('localValorantContent/content.json', 'r', encoding='utf-8') as f:
            try:
                self.content = json.loads(f.readline())
            except:
                print("Error loading the content. Pull a new copy.")
                return
        self.checkContentForAbilities()

    def initialiseMaps(self):
        mapListUrl = 'https://valorant-api.com/v1/maps'
        localMaps = []
        try:
            with urllib.request.urlopen(mapListUrl) as f:
                remoteMaps = json.loads(f.read().decode('utf-8'))['data']
        except:
            print("Error getting remote maps")
            return
        with open('localValorantContent/maps.json', 'r', encoding='utf-8') as f:
            try:
                localMaps = json.loads(f.readline())        
            except:
                pass
        for x in remoteMaps:
            if x not in localMaps:
                localMaps.append(x)
        with open('localValorantContent/maps.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(localMaps))

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Valorant(bot))
