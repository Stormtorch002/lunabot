import discord 
from discord.ext import commands 
import expr 
from num2words import num2words



class ScriptContext:
    def __init__(self, bot, guild, channel, member=None, message=None):
        self.bot = bot 
        self.guild = guild 
        self.channel = channel 
        self.member = member 
        self.message = message 
        self.repls = {} 
        self.magicfuncs = {}

    @classmethod 
    def from_ctx(cls, ctx):
        return cls(ctx.bot, ctx.guild, ctx.channel, ctx.author, ctx.message)
    
    # make a decorator that will add the function to self.repls
    # make it take an optional argument called aliases 

    def repl(self, func, aliases=None):
        self.repls[func.__name__] = func
        if aliases is not None:
            for alias in aliases:
                self.repls[alias] = func
        return func
    
    def magicfunc(self, func, aliases=None):
        self.magicfuncs[func.__name__] = func
        if aliases is not None:
            for alias in aliases:
                self.magicfuncs[alias] = func
        return func

    @repl(aliases=['servername'])
    def server(self):
        """Name of the current server"""
        return self.guild.name
    
    @repl(alises=['servermembercount', 'membercount'])
    def members(self):
        """Number of members in the current server"""
        return len(self.guild.members) 

    @repl(aliases=['serverboosts', 'boostcount'])
    def boosts(self):
        """Number of boosts in the current server"""
        return self.guild.premium_subscription_count
    
    @repl(aliases=['serverboostlevel', 'boosttier', 'serverboosttier'])
    def boostlevel(self):
        """Boost level of the current server"""
        return self.guild.premium_tier

    @repl(aliases=['channelmention'])
    def channel(self):
        """Mention of the current channel"""
        return self.channel.mention
    
    @repl 
    def channelname(self):
        """Name of the current channel"""
        return self.channel.name

    @repl(aliases=['membermention', 'mention'])
    def member(self):
        """Mention of the current member"""
        return self.member.mention
    
    @repl(aliases=['memberavatar', 'pfp', 'memberpfp'])
    def avatar(self):
        """Avatar of the current member"""
        asset = self.member.display_avatar 
        if asset.is_animated():
            return asset.with_format('gif').url 
        else:
            return asset.with_format('png').url

    @repl(aliases=['username'])
    def memberusername(self):
        """Username of the current member"""
        return self.member.name 
    
    @repl(aliases=['memberdisplayname', 'displayname'])
    def membername(self):
        """Display name of the current member"""
        return self.member.display_name 
    
    @magicfunc(alises=['ordinal'])
    def th(self, num: int):
        """Converts a number to its ordinal form"""
        return num2words(num, 'ordinal_num')

    

