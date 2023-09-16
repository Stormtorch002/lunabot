import discord 
from discord.ext import commands 
import expr 
from num2words import num2words


def lunascript_var(aliases=None):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            self.vars[func.__name__] = func
            if aliases is not None:
                for alias in aliases:
                    self.vars[alias] = func
            return func(self, *args, **kwargs)
        return wrapper   
    return decorator

def lunascript_func(aliases=None):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            self.funcs[func.__name__] = func
            if aliases is not None:
                for alias in aliases:
                    self.funcs[alias] = func
            return func(self, *args, **kwargs)
        return wrapper   
    return decorator

class ScriptContext:
    def __init__(self, bot, guild, channel, member=None, message=None):
        self.bot = bot 
        self.guild = guild 
        self.channel = channel 
        self.member = member 
        self.message = message 

        # var_methods = [
        #     self.server,
        #     self.members,
        #     self.boosts,
        #     self.boostlevel,
        #     self.channel,
        #     self.channelname,
        #     self.member,
        #     self.avatar,
        #     self.memberusername,
        #     self.membername
        # ]
        # func_methods = [
        #     self.th
        # ]
        # self.vars = {} 
        # self.funcs = {}
        # for method in var_methods:
        #     method() 
        # for method in func_methods:
        #     method()

    @classmethod 
    def from_ctx(cls, ctx):
        return cls(ctx.bot, ctx.guild, ctx.channel, ctx.author, ctx.message)
    
    # make a decorator that will add the function to self.repls
    # make it take an optional argument called aliases 

    @lunascript_var(aliases=['servername'])
    def server(self):
        """Name of the current server"""
        return self.guild.name

    @lunascript_var(aliases=['membercount', 'servermembercount'])
    def members(self):
        """Number of members in the current server"""
        return len(self.guild.members) 

    @lunascript_var(aliases=['boostcount', 'serverboostcount'])
    def boosts(self):
        """Number of boosts in the current server"""
        return self.guild.premium_subscription_count

    @lunascript_var(aliases=['serverboostlevel', 'boosttier', 'serverboosttier']) 
    def boostlevel(self):
        """Boost level of the current server"""
        return self.guild.premium_tier
 
    @lunascript_var(aliases=['channelmention'])
    def channel(self):
        """Mention of the current channel"""
        return self.channel.mention

    @lunascript_var() 
    def channelname(self):
        """Name of the current channel"""
        return self.channel.name

    @lunascript_var(aliases=['member', 'membermention'])
    def member(self):
        """Mention of the current member"""
        return self.member.mention

    @lunascript_var( aliases = ['memberavatar', 'pfp', 'memberpfp'])
    def avatar(self):
        """Avatar of the current member"""
        asset = self.member.display_avatar 
        if asset.is_animated():
            return asset.with_format('gif').url 
        else:
            return asset.with_format('png').url

    @lunascript_var(aliases=['username'])
    def memberusername(self):
        """Username of the current member"""
        return self.member.name 

    @lunascript_var(aliases = ['name', 'displayname', 'memberdisplayname'])
    def membername(self):
        """Display name of the current member"""
        return self.member.display_name 

    @lunascript_func(aliases=['ordinal'])     
    def th(self, num: int):
        """Converts a number to its ordinal form"""
        return num2words(num, 'ordinal_num')

    

