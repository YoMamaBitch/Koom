import discord
from discord.ext import commands
from discord.ui import Button

def secondsToMinSecString(secs) -> str:
    m,s = divmod(secs,60)
    return f"{m}:{s}"

def generateQueueEmbed(music,author):
    embed = discord.Embed(title="Queue List", color=0xc98847)
    embed.set_footer(text=f"Requested by {author.display_name}")
    songNames = '\u200b'
    songDurations = '\u200b'
    for x in range(music.queueStart, music.queueEnd):
        if len(music.queue) == x:
            break
        truncated = music.queue[x]['title']
        if len(truncated) > 19:
            truncated = truncated[0:18] + '...'
        songNames += f'{x}. ' + truncated + '\n'
        songDurations += music.queue[x]['duration'] + '\n'
    embed.add_field(name="Name", value=songNames)
    embed.add_field(name='\u200b', value='\u200b')
    embed.add_field(name="Length", value=songDurations)
    return embed

class QueueButton(Button):
    def __init__(self, pStyle=discord.ButtonStyle.grey, pEmoji=None, musicCog = None, author = None):
        super().__init__(style=pStyle, emoji=pEmoji)
        self.music = musicCog
        self.author = author
        if self.emoji == '⬅️':
            if self.music.queueStart == 0:
                self.diabled = True
        elif self.emoji == '➡️':
            if self.music.queueEnd < 10:
                self.disabled = True

    def checkButton(self, btn):
        if btn.emoji.name == '⬅️': 
            if self.music.queueStart == 0:
                btn.disabled = True
            else:
                btn.disabled = False
        elif btn.emoji.name == '➡️':
            if self.music.queueEnd >= len(self.music.queue):
                btn.disabled = True
            else:
                btn.disabled = False

    async def callback(self,interaction):
        if self.emoji.name == '⬅️': 
            self.music.queueStart -= 10
            self.music.queueEnd -= 10
        elif self.emoji.name == '➡️':
            self.music.queueStart += 10
            self.music.queueEnd += 10
        
        children = self.view.children
        for x in children:
            self.checkButton(x)
        
        #await interaction.response.edit_message(content='\u200b',view=self.view)
        embed = generateQueueEmbed(self.music, self.author)
        await interaction.response.edit_message(embed=embed,view=self.view)
        # if self.emoji.name == '⬅️':
        #     if self.music.queueStart == 0:
        #         self.disabled = True
        #         await interaction.response.edit_message(content='\u200b',view=self.view)
        #         return
        #     self.music.queueStart -= 10
        #     self.music.queueEnd -= 10
        #     self.diabled = False
        #     embed = generateQueueEmbed(self.music, self.author)
        #     await interaction.response.edit_message(embed=embed,view=self.view)
        # elif self.emoji.name == '➡️':
        #     if self.music.queueEnd >= len(self.music.queue):
        #         self.disabled = True
        #         await interaction.response.edit_message(content='\u200b',view=self.view)
        #         return
        #     self.music.queueStart += 10
        #     self.music.queueEnd += 10
        #     self.disabled = False
        #     embed = generateQueueEmbed(self.music, self.author)
        #     await interaction.response.edit_message(embed=embed,view=self.view)
