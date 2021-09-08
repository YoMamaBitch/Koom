import asyncio
import discord
from discord.ext import commands
from discord.ext.commands.core import command
import youtube_dl

class Music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.ctx = None
        self.voice = None
        self.pointer = 0
        self.queue = []
        self.bReachedEnd = False
        self.bLoop = False
        
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):   
        if before.channel is not None and after.channel is None:
            self.queue = []
            self.pointer = -1
            self.voice = None
            self.bLoop = False
            self.bReachedEnd = False

    
    @commands.command(aliases=['play','p'])
    async def _play(self, pCtx, *inputStr : str):
        if not pCtx.message.author.voice:
            await pCtx.send("You are not in a voice chat!")
            return
        else:
            print(self.pointer)
            await self._summon(pCtx)
            request = ' '.join(inputStr)
            await self._enqueue(pCtx, request)
            print(self.pointer)
        if not pCtx.message.author.voice:
            await pCtx.send("You are not in a voice chat")
        elif pCtx.message.author.voice.channel.id is not self.voice.channel.id and self.voice is not None:
            await pCtx.send("Bot is in use in another chat!")
        else:
            print(self.pointer)
            self._playSong(pCtx)
            print(self.pointer)

    @commands.command(name='remove')
    async def _remove(self, pCtx, args):
        try:
            posToRemove = int(args)
        except:
            await pCtx.send("Enter a valid integer")
            return
            
        if self.pointer == posToRemove:
            await self._skip(pCtx)
        if self.pointer >= posToRemove:
            self.pointer-=1
        itemRemoved = self.queue.pop(posToRemove)
        await pCtx.send("Removed: " + itemRemoved['title'])


    @commands.command(aliases=['join','summon'])
    async def _summon(self, pCtx):
        if not pCtx.message.author.voice:
            await pCtx.send("You're not in a voice channel cunt")
            return
        if self.voice is None:
            await self._connect(pCtx)
            self.ctx = pCtx

    @commands.command(aliases=['queue', 'q'])
    async def _queue(self,pCtx):
        if not self.voice:
            await pCtx.send("I'm not in a chat cunt")
            return
        embed = discord.Embed()
        queueList = ''
        counter = 0
        for item in self.queue:
            queueList += '**' + str(counter) + '**' + '. '
            queueList += f"[{item['title']}]({item['webpage_url']})"
            queueList += ' | Request by: ' + item['author'] + '\n'
            counter += 1
        embed.add_field(name='Queue', value=queueList)
        if queueList == '':
            await pCtx.send("There is nothing in the queue!")
        else:
            await pCtx.send(embed=embed)

    @commands.command(name='resume')
    async def _resume(self,pCtx):
        self.voice = discord.utils.get(self.bot.voice_clients, guild=pCtx.guild)
        if self.voice.is_paused():
            self.voice.resume()
        else:
            await pCtx.send("Audio not paused.")

    @commands.command(name='stop')
    async def _stop(self,pCtx):
        self.voice = discord.utils.get(self.bot.voice_clients, guild=pCtx.guild)
        self.voice.stop()

    @commands.command(name='pause')
    async def _pause(self, pCtx):
        self.voice = discord.utils.get(self.bot.voice_clients, guild=pCtx.guild)
        if self.voice.is_playing():
            self.voice.pause()
        else:
            await pCtx.send("No audio playing.")

    @commands.command(aliases=['lq','loopqueue','loopq'])
    async def _loopQueue(self, pCtx):
        self.bLoop = not self.bLoop
        if self.bLoop:
            await pCtx.send("Now looping queue!")
            self.bReachedEnd = False
        else:
            await pCtx.send("Now un-looping queue!")
            if (self.pointer == len(self.queue)-1):
                self.bReachedEnd = True

    @commands.command(aliases=['dc','disconnect'])
    async def _disconnectBot(self, pCtx):
        self.queue = []
        self.pointer = 0
        self.voice = discord.utils.get(self.bot.voice_clients, guild=pCtx.guild)
        try:
            if self.voice.is_connected():
                await self.voice.disconnect()
                self.voice = None
                self.ctx = None
            else:
                await pCtx.send("Koom not in a voice chat!")
        except:
            return False
            

    @commands.command(name='skip')
    async def _skip(self,pCtx):
        prevSongTitle = ''
        self.voice = discord.utils.get(self.bot.voice_clients, guild=pCtx.guild)
        if self.voice is None:
            await pCtx.send("Koom is not in a chat!")
            return False
        if len(self.queue) > 0:
            prevSongTitle = self.queue[self.pointer]['title']
            self._incrementPointer()
            if not self.bReachedEnd or self.bLoop:
                try:
                    self.voice.stop()
                except:
                    return False
                await pCtx.send(f"Skipped song: [{prevSongTitle}]")
                self._playSong(pCtx)
                currSongTitle = self.queue[self.pointer]['title']
                await pCtx.send(f"Now playing: [{currSongTitle}]")
                return
            try:
                self.voice.stop()
            except:
                return False
            await pCtx.send("Reached end of queue!")
    
    def _incrementPointer(self):
        self.pointer += 1
        if self.pointer >= len(self.queue):
            if self.bLoop:
                self.pointer = 0
            else:
                self.bReachedEnd = True

    async def _connect(self, pCtx):
        voiceChannel = self.bot.get_channel(pCtx.author.voice.channel.id)
        await voiceChannel.connect()
        self.voice = discord.utils.get(self.bot.voice_clients, guild=pCtx.guild)
    
    async def _enqueue(self, pCtx, inputStr : str):
        successMsg = ":white_check_mark: Successfully Added!\n"
        ydl_opts = {'format':'bestaudio/best','postprocessors': [{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}], 'yes-playlists':True}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            if inputStr.startswith('http'):
                info = ydl.extract_info(inputStr, download=False)
                entry = {
                    'title' : info['title'], 
                    'hostURL' : info['url'], 
                    'webpage_url' : info['webpage_url'],
                    'author' : pCtx.message.author.display_name}
                self.queue.append(entry)
                await pCtx.send(successMsg + "%s" % entry['title'] + "\n(%s)" % entry['webpage_url'])
            else:
                try:
                    info = ydl.extract_info("ytsearch:%s" % inputStr, download=False)['entries'][0]
                    entry = {
                    'title' : info['title'], 
                    'hostURL' : info['url'], 
                    'webpage_url' : info['webpage_url'],
                    'author' : pCtx.message.author.display_name}
                    self.queue.append(entry)
                    await pCtx.send(successMsg + "%s" % entry['title'] + "\n(%s)" % entry['webpage_url'])
                except Exception as e:
                    await pCtx.send('Error: ' + str(e))
                    return False

    
    def _playSong(self,pCtx):
        FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        try:
            self.voice.play(discord.FFmpegPCMAudio(self.queue[self.pointer]['hostURL'], **FFMPEG_OPTIONS), after=lambda e: self.after_song(pCtx))    
        except Exception as e:
            #await pCtx.send('Error: ' + str(e))
            return False

    def after_song(self, pCtx):
        self._incrementPointer()
        if not self.bReachedEnd or self.bLoop:
            self._playSong(pCtx)

    @commands.command(name='help')
    async def _helpMenu(self,pCtx):
        helpCommands = ''
        helpExplanation = ''
        with open('helpText.txt') as file:
            for line in file:
                helpCommands += line.split('--')[0] + '\n'
                helpExplanation += line.split('--')[1]

        embed = discord.Embed(title="Scuffed Help V0.3", color=0xe0e0e0)
        embed.add_field(name='Commands', value=helpCommands)
        embed.add_field(name='\u200b', value=helpExplanation)
        embed.add_field(name='\u200b', value="Again, it's not even remotely close to being done so there's a lot of commands missing... Bite me.", inline=False)
        await pCtx.send(embed=embed)

    
def setup(bot):
    bot.add_cog(Music(bot))