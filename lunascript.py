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
        self.vars = {} 
        self.funcs = {}
        for name, func in self.__class__.__dict__.items():
            if func.var:
                self.vars[name] = func 
            else:
                self.funcs[name] = func

    @classmethod 
    def from_ctx(cls, ctx):
        return cls(ctx.bot, ctx.guild, ctx.channel, ctx.author, ctx.message)
    
    # make a decorator that will add the function to self.repls
    # make it take an optional argument called aliases 

    # def repl(self, func, aliases=None):
        # self.repls[func.__name__] = func
        # if aliases is not None:
            # for alias in aliases:
                # self.repls[alias] = func
        # return func
    
    # def magicfunc(self, func, aliases=None):
        # self.magicfuncs[func.__name__] = func
        # if aliases is not None:
            # for alias in aliases:
                # self.magicfuncs[alias] = func
        # return func

    def server(self):
        """Name of the current server"""
        var = True 
        aliases = ['server', 'servername']
        return self.guild.name
    
    def members(self):
        """Number of members in the current server"""
        var = True 
        aliases = ['members', 'membercount', 'servermembercount']
        return len(self.guild.members) 

    def boosts(self):
        """Number of boosts in the current server"""
        var = True 
        aliases = ['boosts', 'boostcount', 'serverboostcount']
        return self.guild.premium_subscription_count
    
    def boostlevel(self):
        """Boost level of the current server"""
        var = True 
        aliases = ['boostlevel', 'serverboostlevel', 'boostslevel', 'serverboostslevel']
        return self.guild.premium_tier

    def channel(self):
        """Mention of the current channel"""
        var = True 
        aliases = ['channel', 'channelmention']
        return self.channel.mention
    
    def channelname(self):
        var = True 
        aliases = ['channelname']
        """Name of the current channel"""
        return self.channel.name

    def member(self):
        """Mention of the current member"""
        var = True 
        aliases = ['member', 'membermention']
        return self.member.mention
    
    def avatar(self):
        """Avatar of the current member"""
        var = True 
        aliases = ['avatar', 'memberavatar', 'pfp', 'memberpfp']
        asset = self.member.display_avatar 
        if asset.is_animated():
            return asset.with_format('gif').url 
        else:
            return asset.with_format('png').url

    def memberusername(self):
        """Username of the current member"""
        var = True 
        aliases = ['memberusername', 'username']
        return self.member.name 
    
    def membername(self):
        """Display name of the current member"""
        var = True 
        aliases = ['membername', 'name', 'displayname', 'memberdisplayname']
        return self.member.display_name 
    
    def th(self, num: int):
        """Converts a number to its ordinal form"""
        var = False 
        aliases = ['th', 'ordinal']
        return num2words(num, 'ordinal_num')

    

