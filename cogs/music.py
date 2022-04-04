import discord,secrets, asyncio, youtube_dl, utility
from discord.ext import commands
from random import seed, randint

ydl_opts = {'format':'bestaudio/best','postprocessors': [{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}], 'yes-playlists':True}
ydl = youtube_dl.YoutubeDL(ydl_opts)

class Music(commands.Cog):
    def __init__(self,bot:commands.Bot)->None:
        self.bot = bot
        self.queuePointer = 0
        self.queue = []
        self.voiceChannel = None
        self.reachedEnd = False
        self.loop = False
        self.loopQueue = False
        self.timeout = 0

    @commands.command(aliases=['play','p'])
    async def queue_song(self, ctx, *input : str):
        arg = ' '.join(input)
        if self.is_url(arg):
            info = ydl.extract_info(arg, download=False)
        else:
            info = ydl.extract_info(f"ytsearch:{arg}", download=False)['entries'][0]
        duration = utility.secondsToMinSecString(int(info['duration']))
        data = {
            'title' : info['title'],
            'hostURL' : info['url'],
            'webpage_url' : info['webpage_url'],
            'duration' : duration,
            'thumbnail': info['thumbnails'][3]['url'],
            'author' : ctx.message.author.display_name }
        self.queue.append(data)
        await self.send_success_queue(ctx, data)
        self.tryPlay(ctx)


    def tryPlay(self,ctx):
        if ctx.voice_client.is_playing():
            return
        self.play(ctx)

    def play(self, ctx, seek = 0):
        FFMPEG_OPT =  {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': f'-vn -ss {seek}'}
        try:
            url = self.queue[self.queuePointer]['hostURL']
            ctx.voice_client.play(discord.FFmpegPCMAudio(url), **FFMPEG_OPT, after=lambda e: self.post_song(ctx))
        except Exception as e:
            print(e)            

    def post_song(self, ctx):
        if self.loop:
            self.play(self,ctx)
            return
        self.incrementPointer()
        if not self.reachedEnd:
            self.play(self,ctx)

    def incrementPointer(self):
        if self.loopQueue:
            if self.queuePointer >= len(self.queue):
                self.queuePointer = 0
                self.reachedEnd = False
                return
        if self.queuePointer >= len(self.queue):
            self.reachedEnd = True
            return
        self.reachedEnd = False
        self.queuePointer = self.queuePointer + 1

    def is_url(self, argument:str):
        return argument.startswith("http")

    @queue_song.before_invoke
    async def ensure_voice_connect(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()
    
    ######## OUTPUT EMBEDS ########
    async def send_success_queue(self,ctx,data):
        embed = discord.Embed(title="Queued Song", color=0x37a7db)
        embed.add_field(name="Song Name", value=data['title'], inline=False)
        embed.add_field(name="Duration", value=data['duration'], inline=False)
        embed.set_footer(text=f"Requested by {data['author']}")
        await ctx.send(content=data['webpage_url'],embed=embed)

    async def send_playing_message(self,ctx):
        data = self.queue[self.queuePointer]
        embed = discord.Embed(title="Now Playing", color=0x26d437)
        embed.add_field(name="Song Name", value=data['title'], inline=False)
        embed.add_field(name="Duration", value=data['duration'], inline=False)
        embed.set_footer(text=f"Requested by {data['author']}")
        await ctx.send(content=data['webpage_url'],embed=embed)
    ###############################

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot), guild=secrets.testGuild)
