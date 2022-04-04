import discord
from discord.ext import commands

def secondsToMinSecString(secs) -> str:
    m,s = divmod(secs,60)
    return f"{m}:{s}"