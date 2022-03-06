import asyncio
import secrets
import discord
from random import seed
from random import randint
from discord.ext import commands
import youtube_dl

class Music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.ctx = None
        self.voice = None
        self.pointer = 0
        self.queue = []
        self.bReachedEnd = False
        self.bLoopQueue = False
        self.bLoop = False
        self.bIgnoreAfter = False
        self.time = 0
        
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):   

        if self.voice is None and self.ctx is not None:
            self.voice = discord.utils.get(self.bot.voice_clients, guild=self.ctx.guild)

        if before.channel is not None and after.channel is None:
            self.queue = []
            self.pointer = 0
            self.voice = None
            self.bLoopQueue = False
            self.bLoop = False
            self.bReachedEnd = False
        elif before.channel is None:
            while True:
                await asyncio.sleep(1)
                if self.voice is None:
                    return
                self.time = self.time + 1
                if self.voice.is_playing() and not self.voice.is_paused():
                    self.time = 0
                if self.time == 600: 
                    await self.ctx.send("Bot disconnected due to inactivity")
                    await self._disconnectBot(self.ctx)
                    return
                if not self.voice.is_connected():
                    break

    @commands.command(aliases=['forcejoin','sendbot'])
    async def _sendbotToChannel(self, pCtx, *inputStr):
        my_input = ' '.join(inputStr)
        if pCtx.message.author.id != secrets.keironID:
            return
        if self.voice is not None:
            await self.voice.move_to(int(my_input.split(' ')[0]))
        else:
            voiceChannel = self.bot.get_channel(int(my_input.split(' ')[0]))
        if voiceChannel is None:
            print("Despacito")
        await voiceChannel.connect()
        self.voice = discord.utils.get(self.bot.voice_clients, guild=pCtx.guild)
        tt = my_input.split(' ')[1]
        await self._enqueue(pCtx, my_input.split(' ')[1])
        await self._playSong(pCtx)
        

    @commands.command(aliases=['shuffle'])
    async def _shuffle(self, pCtx):
        seed(69)
        queueLength = len(self.queue)
        count = randint(queueLength * 2,  queueLength * 5)
        for _ in range(count):
            index1 = randint(1,queueLength-1)
            index2 = randint(1,queueLength-1)
            temp = self.queue[index1]
            self.queue[index1] = self.queue[index2]
            self.queue[index2] = temp
        await pCtx.send("Shuffled the queue")
        
    @commands.command(aliases=['seek','goto'])
    async def _seekSong(self,pCtx,inputStr : str):
        secondsTime = 0
        try:
            secondsTime = int(inputStr)
        except:
            parsedTime = inputStr.split(':')
            seconds = parsedTime.pop()
            minutes = parsedTime.pop()
            hours = parsedTime.pop()
            secondsTime = seconds + (minutes*60) + (hours*3600)
        if self.voice is not None:
            if self.voice.is_playing():
                self.voice.stop()
                
        if self.voice is None:
            await pCtx.send("Am I in a channel?")
            return
        self.bIgnoreAfter = True
        if self.voice.is_playing():
            self.voice.stop()
        self._playSong(pCtx, secondsTime)
        await pCtx.send(f"Skipping to {secondsTime}s")

    @commands.command(aliases=['clear','wipe'])
    async def _wipequeue(self,pCtx):
        if self.voice is not None and self.voice.is_playing():
            self.voice.stop()
        self.queue = []
        await asyncio.sleep(1)
        self.pointer = 0
        await pCtx.send("Cleared queue")
            
    @commands.command(aliases=['play','p'])
    async def _play(self, pCtx, *inputStr : str):
        if not pCtx.message.author.voice:
            await pCtx.send("You are not in a voice chat!")
            return
        else:
            if self.voice is None:
                await self._summon(pCtx)
            request = ' '.join(inputStr)
            await self._enqueue(pCtx, request)
        if not pCtx.message.author.voice:
            await pCtx.send("You are not in a voice chat")
        elif pCtx.message.author.voice.channel.id is not self.voice.channel.id and self.voice is not None:
            await pCtx.send("Bot is in use in another chat!")
        else:
            self._playSong(pCtx)

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
            print("You're not in a voice chat for me to join")
            await pCtx.send("You're not in a voice channel :(")
            return

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

    @commands.command(name='pause')
    async def _pause(self, pCtx):
        self.voice = discord.utils.get(self.bot.voice_clients, guild=pCtx.guild)
        if self.voice.is_playing():
            self.voice.pause()
        else:
            await pCtx.send("No audio playing.")

    @commands.command(aliases=['lq','loopqueue','loopq'])
    async def _loopQueue(self, pCtx):
        self.bLoopQueue = not self.bLoopQueue
        if self.bLoopQueue:
            if (self.pointer >= len(self.queue)):
                self.pointer = 0
            await pCtx.send("Now looping queue!")
            self.bReachedEnd = False
        else:
            await pCtx.send("Now un-looping queue!")
            if (self.pointer == len(self.queue)-1):
                self.bReachedEnd = True

    @commands.command(aliases=['loop', 'l'])
    async def _loopSong(self,pCtx):
        self.bLoop = not self.bLoop
        if self.bLoop:
            await pCtx.send("Now looping the current song.")
            if self.bReachedEnd:
                self.bReachedEnd = False
                if not self.voice.is_playing():
                    self.pointer = self.pointer - 1
                    self._playSong(pCtx)
        else:
            await pCtx.send("Now un-looping the current song.")
            if self.pointer >= len(self.queue):
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
        self.voice = discord.utils.get(self.bot.voice_clients, guild=pCtx.guild)
        if self.voice is None:
            await pCtx.send("Koom is not in a chat!")
            return False
        if len(self.queue) > 0:
            if not self.bReachedEnd or self.bLoopQueue or self.bLoop:
                try:
                    self.voice.stop()
                except:
                    return False
                await pCtx.send(f"Skipped song")
                self._playSong(pCtx)
                currSongTitle = self.queue[self.pointer]['title']
                await pCtx.send(f"Now playing: [{currSongTitle}]")
                return
            try:
                self.voice.stop()
            except:
                return False
            await pCtx.send("Reached end of queue!")
    
    @commands.command(name='pointer')
    async def _getPointer(self, pCtx):
        await pCtx.send(f"Pointer: {self.pointer}")

    def _incrementPointer(self):
        if (self.bLoop):
            return
        self.pointer += 1
        if self.pointer >= len(self.queue):
            if self.bLoopQueue:
                self.pointer = 0
            else:
                self.bReachedEnd = True

    async def _connect(self, pCtx):
        voiceChannel = pCtx.author.voice.channel
        await voiceChannel.connect()
        await pCtx.guild.change_voice_state(channel=voiceChannel, self_mute=False, self_deaf=True)
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

    def _playSong(self,pCtx, optionalSeek = 0):
        FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': f'-vn -ss {optionalSeek}'}
        try:
            self.voice.play(discord.FFmpegPCMAudio(self.queue[self.pointer]['hostURL'], **FFMPEG_OPTIONS), after=lambda e: self.after_song(pCtx))    
        except Exception as e:
            #print(e)
            #loop = asyncio.get_event_loop()
            #loop.create_task(self.send_song_error_msg(e))
            print('Error playing song: ' + str(e))
            return False

    def after_song(self, pCtx):
        if self.bIgnoreAfter:
            self.bIgnoreAfter = False
            return
        self._incrementPointer()
        if not self.bReachedEnd or self.bLoopQueue or self.bLoop:
            self._playSong(pCtx)

    async def send_song_error_msg(self,error):
        await self.ctx.send('Error playing song: ' + str(error))

    
def setup(bot):
    bot.add_cog(Music(bot))