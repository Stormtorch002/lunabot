import discord 
from discord.ext import commands 
import expr 
from num2words import num2words
import re


def clean(token):
    try:
        token = int(token)
    except ValueError:
        try:
            token = float(token)
        except ValueError:
            repl = r'\"'
            token = f'''"{token.replace('"', repl)}"'''
    return token 


class ScriptContext:
    def __init__(self, bot, guild, channel, member=None, message=None):
        self.bot = bot 
        self.guild = guild 
        self.channel = channel 
        self.member = member 
        self.message = message 
        self.vars = self.bot.vars

        self.vars_builtin_tuples = {
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
        self.funcs_tuples = {
            ('th', 'ordinal'): self.th
        }
        self.vars_builtin = {}
        for k, v in self.vars.items():
            for n in k:
                self.vars_builtin[n] = v
        self.funcs = {}
        for k, v in self.funcs.items():
            for n in k:
                self.funcs[n] = v
        

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

    def th(self, num: str):
        """Converts a number to its ordinal form"""
        return num2words(int(num), 'ordinal_num')

    
class TextEmbed:
    def __init__(self, text=None, embed=None):
        self.text = text 
        self.embed = embed 


class LunaScript(TextEmbed):

    def __init__(self, msgble, text=None, embed=None, **kwargs):
        super().__init__(text, embed)
        if isinstance(msgble, commands.Context):
            self.script_ctx = ScriptContext.from_ctx(msgble)
            self.msgble = self.script_ctx.channel
        else:
            if 'channel' in kwargs:
                channel = kwargs.pop('channel')
            else:
                channel = msgble

            self.script_ctx = ScriptContext(channel=channel, **kwargs)
            self.msgble = msgble
        self.parser = LunaScriptParser(self.script_ctx)

    async def send(self):
        try:
            print(self.text)
            print(self.embed)
            await self.msgble.send(await self.parser.parse(self.text), embed=await self.transform_embed())
        except LunaScriptError as e:
            await self.msgble.send(f'An error occurred while parsing the LunaScript: `{e}`')

    async def transform_embed(self):
        if self.embed is None:
            return 
        if self.embed.title:
            self.embed.title = await self.parser.parse(self.embed.title)
        if self.embed.description:
            self.embed.description = await self.parser.parse( self.embed.description)
        for field in self.embed.fields:
            field.name = await self.parser.parse(field.name)
            field.value = await self.parser.parse(field.value)
        if self.embed.author.name is not None:
            self.embed.set_author(name=await self.parser.parse( self.embed.author.name), icon_url=self.embed.author.icon_url)
        if self.embed.footer.text is not None:
            self.embed.set_footer(text=await self.parser.parse( self.embed.footer.text), icon_url=self.embed.footer.icon_url)
        return self.embed
        

# class Bracket:
#     def __init__(self, beg, end, brktype, funcname=None):
#         self.beg = beg 
#         self.end = end 
#         self.brktype = brktype 
#         self.funcname = funcname

class LunaScriptError(Exception):
    pass

class UnmatchedBracket(LunaScriptError):
    pass

class InvalidMathExpression(LunaScriptError):
    pass 

class InvalidFunctionArgs(LunaScriptError):
    pass 

class InvalidCondition(LunaScriptError):
    pass



class LunaScriptParser:

    def __init__(self, script_ctx):
        self.script_ctx = script_ctx
        self.vars_builtin = self.script_ctx.vars_builtin
        self.funcs = self.script_ctx.funcs
        self.vars = self.script_ctx.bot.vars 

    async def parse(self, text):
        return await self.script_ctx.bot.loop.run_in_executor(None, self.parse_sync, text)

    def parse_sync(self, text):
        
        def ordered_eval(string):
            string = [char for char in string]
            newstr = []
            i = 0
            while i < len(string):
                if i > 0 and string[i-1] == '\\':
                    newstr.append(string[i])
                    i += 1
                    continue
                if string[i] == '[':
                    # find the closing bracket
                    counter = 0
                    j = i+1

                    found = False
                    while j < len(string):
                        if string[j] == '[' and string[j-1] != '\\':
                            counter += 1
                        elif string[j] == ']' and string[j-1] != '\\':
                            if counter == 0:
                                found = True
                                break 
                            else:
                                counter -= 1 
                        j += 1  
                    if not found:
                        raise UnmatchedBracket(f'Unmatched bracket: [')

                    inside = ordered_eval(string[i+1:j])

                    match = re.match(r'(\d+|(?:.+?))\s*(<|<=|=<|==|=|=>|>=|>)\s*(\d+|(?:.+?)):[ ]?', inside)
                    if match is None:
                        raise InvalidCondition(f'Invalid condition in {inside}')
                    
                    left = match.group(1)
                    left = clean(left)
                    op = match.group(2)
                    if op == '=':
                        op = '=='
                    right = match.group(3)
                    right = clean(right)

                    if eval(f'{left} {op} {right}') is True:
                        newstr.extend([char for char in inside[match.end():]])

                    i += j - i + 1
                elif string[i] == '(':
                    k = i-1
                    while k > 0 and string[k] != ' ':
                        k -= 1
                    funcname = ''.join(string[k+1:i])
                    if funcname not in self.funcs:
                        newstr += string[i]
                        i += 1
                        continue
                    # find the closing bracket
                    counter = 0
                    j = i+1
                    found = False

                    while j < len(string):
                        if string[j] == '(':
                            counter += 1
                        elif string[j] == ')':
                            if counter == 0:
                                found = True
                                break 
                            else:
                                counter -= 1 
                        j += 1  
                    if not found:
                        raise UnmatchedBracket(f'Unmatched bracket: (')

                    inside = ordered_eval(string[i+1:j])
                    args = inside.split(',')
                    args = [arg.strip() for arg in args]
                    func = self.funcs[funcname]
                    try:
                        repl = func(*args)
                    except TypeError:
                        raise InvalidFunctionArgs(f'Invalid arguments for {funcname}: {inside}')
                    for _ in range(len(funcname)):
                        newstr.pop()
                    newstr.extend([char for char in str(repl)])

                    i += j - i + 1
                elif string[i] == '$':
                    # find next $ 
                    j = i+1
                    found = False 

                    while j < len(string):
                        if string[j] == '$' and string[j-1] != '\\':
                            found = True
                            break
                        j += 1
                    if not found:
                        raise UnmatchedBracket(f'Unmatched bracket: $')

                    inside = ordered_eval(string[i+1:j])
                    try:
                        repl = expr.evaluate(inside)
                    except Exception:
                        raise InvalidMathExpression(f'Invalid math expression: {inside}')
                    newstr.extend([char for char in str(repl)])
                    i += j - i + 1
                elif string[i] == '<':
                    if i >= len(string) - 2 or string[i+1].lower() != 's' or string[i+2] != '>':
                        newstr += string[i]
                        i += 1
                        continue
                    
                    j = i+3
                    found = False
                    while j < len(string) - 3:
                        if string[j:j+4] in (['<', '/', 's', '>'], ['<', '/', 'S', '>']):
                            found = True
                            break
                        j += 1

                    if not found:
                        raise UnmatchedBracket(f'Unmatched bracket: <s>')

                    def inner():
                        vars = [
                            ('bot', 'self.script_ctx.bot'), 
                            ('server', 'self.script_ctx.guild'), 
                            ('channel', 'self.script_ctx.channel'), 
                            ('member', 'self.script_ctx.member'), 
                            ('message', 'self.script_ctx.message')
                        ]
                        for name, val in vars:
                            exec(f'{name} = {val}', locals(), locals())
                        for name, val in self.vars.items():
                            if isinstance(val, str):
                                repl = '\\"'
                                val = '"' + val.replace('"', repl) + '"'
                            exec(f'{name} = {val}', locals(), locals())
                        exec(''.join(string[i+3:j]))
                        g = locals() 
                        if 'updates' in g:
                            for varname in g['updates'].split():
                                if varname in g:
                                    self.vars[varname] = g[varname]
                                    self.script_ctx.bot.vars[varname] = g[varname]
                    inner()
                    i += j - i + 4
                elif string[i] == '{':
                    j = i+1
                    while j < len(string) and string[j] != '}':
                        j += 1
                    varname = ''.join(string[i+1:j])
                    if varname in self.vars_builtin:
                        repl = self.vars_builtin[varname]
                    elif varname in self.vars:
                        repl = self.vars[varname]
                    else:
                        repl = ''
                    newstr.extend([char for char in str(repl)])
                    i += j - i + 1
                else:
                    newstr.append(string[i])
                    i += 1

            return ''.join(newstr)
        
        return ordered_eval(text)