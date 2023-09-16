import discord 
from discord.ext import commands 
import expr 
from num2words import num2words


def lunascript_var(aliases=None):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            print('hi lol')
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
            print('hi lol')
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
        # for method in var_methods:
        #     method() 
        # for method in func_methods:
        #     method()

        # make a dict where the key is a tuple of the aliases and the value is the function

        self.vars = {
            ('server', 'servername'): self.servername,
            ('members', 'membercount', 'servermembercount'): self.membercount,
            ('boosts', 'boostcount', 'serverboostcount'): self.boosts,
            ('boostlevel', 'serverboostlevel', 'boosttier', 'serverboosttier'): self.boostlevel,
            ('channel', 'channelmention'): self.channelmention,
            ('channelname',): self.channelname,
            ('member', 'membermention'): self.membermention,
            ('avatar', 'memberavatar', 'pfp', 'memberpfp'): self.avatar,
            ('memberusername', 'username'): self.memberusername,
            ('membername', 'name', 'displayname', 'memberdisplayname'): self.membername
        }
        self.funcs = {
            ('th', 'ordinal'): self.th
        }

    @classmethod 
    def from_ctx(cls, ctx):
        return cls(ctx.bot, ctx.guild, ctx.channel, ctx.author, ctx.message)
    
    # make a decorator that will add the function to self.repls
    # make it take an optional argument called aliases 

    def servername(self):
        """Name of the current server"""
        return self.guild.name

    def membercount(self):
        """Number of members in the current server"""
        return len(self.guild.members) 

    def boosts(self):
        """Number of boosts in the current server"""
        return self.guild.premium_subscription_count

    def boostlevel(self):
        """Boost level of the current server"""
        return self.guild.premium_tier
 
    def channelmention(self):
        """Mention of the current channel"""
        return self.channel.mention

    def channelname(self):
        """Name of the current channel"""
        return self.channel.name

    def membermention(self):
        """Mention of the current member"""
        return self.member.mention

    def avatar(self):
        """Avatar of the current member"""
        asset = self.member.display_avatar 
        if asset.is_animated():
            return asset.with_format('gif').url 
        else:
            return asset.with_format('png').url

    def memberusername(self):
        """Username of the current member"""
        return self.member.name 

    def membername(self):
        """Display name of the current member"""
        return self.member.display_name 

    def th(self, num: int):
        """Converts a number to its ordinal form"""
        return num2words(num, 'ordinal_num')

    

