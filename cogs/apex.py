import discord
import json
from discord.ext import commands
import secrets
import asyncio
import requests

class Apex(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.baseurl = "https://public-api.tracker.gg/v2/apex/standard/profile/"

    @commands.command(aliases=['apex_test', 'apextest'])
    async def _apex_test(self ,pCtx, *Name):
        player_name = ' '.join(Name)
        if player_name.endswith(('xbox', 'XBOX','Xbox','XBox','XBOx','xBox','xBOx','xBOX')):
            player_name = player_name.removesuffix('xbox')
            platform = 'xbox'
        elif player_name.endswith(('psn','PSN','pSN','Psn','psN','PSn')):
            player_name = player_name.removesuffix('psn')
            platform = 'psn'
        elif player_name.endswith(('pc','PC','origin','Origin','Pc')):
            platform = 'origin'
            player_name = player_name.removesuffix('pc')
            player_name = player_name.removesuffix('origin')
        else:
            platform = 'origin'

        my_headers = {'TRN-Api-Key':secrets.trackerggKey, 'Accept':'application/json', 'Accept-Encoding':'gzip'}
        try:
            req = requests.get(self.baseurl + platform + '/' + player_name, headers=my_headers)
        except Exception as e:
            print(e)
        my_json = json.loads(req.text)
        test = 0

def setup(bot):
    bot.add_cog(Apex(bot))