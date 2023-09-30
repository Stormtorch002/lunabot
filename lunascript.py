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
            token = r'\"'
            token = f'''"{token.replace('"', repl)}"'''
    return token 

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
        self.vars = self.bot.vars

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

    def __init__(self, ctx, text=None, embed=None):
        super().__init__(text, embed)
        self.ctx = ctx
        self.script_ctx = ScriptContext.from_ctx(self.ctx)
        self.parser = LunaScriptParser(self.script_ctx)

    def transform_embed(self):
        if self.embed is None:
            return 
        if self.embed.title:
            self.embed.title = self.parser.parse(self.embed.title)
        if self.embed.description:
            self.embed.description = self.parser.parse( self.embed.description)
        for field in self.embed.fields:
            field.name = self.parser.parse( field.name)
            field.value = self.parser.parse( field.value)
        if self.embed.author.name is not None:
            self.embed.set_author(name=self.parser.parse( self.embed.author.name), icon_url=self.embed.author.icon_url)
        if self.embed.footer.text is not None:
            self.embed.set_footer(text=self.parser.parse( self.embed.footer.text), icon_url=self.embed.footer.icon_url)
        
    def transform(self):
        if self.text is None and self.embed is None:
            return None
        if self.embed is not None:
            self.transform_embed()
        if self.text is not None:
            self.text = self.parser.parse(self.text) 

        return TextEmbed(self.text, self.embed)
        if self.text is not None and self.embed is not None:
            return self.text, self.embed
        elif self.text is not None:
            return self.text
        elif self.embed is not None:
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

    def parse(self, text):
        
        # vars = re.findall(r'[^\\]\{([a-zA-Z0-9_]+)\}', self.text)
        # for var in vars:
        #     if var in self.vars_builtin:
        #         repl = self.vars_builtin[var]()
        #     elif var in self.vars:
        #         repl = self.vars[var]
        #     else:
        #         continue
        #     self.text = self.text.replace(f'{{{var}}}', repl)
        
        # conds = []
        # funcs = []
        # exprs = []
        # indices = {}
        # ignore_closing_paren = False

        # script_tags = re.finditer(r'<[Ss]>(.+?)</[Ss]>', self.text, re.DOTALL)
        # # find all the starting indices
        # for tag in script_tags:
        #     beg = tag.start() + 3
        #     end = tag.end() - 4
        #     brk = Bracket(beg, end, 'script')
        #     indices[beg] = brk 

        # for i, char in enumerate(self.charlst):
        #     if i > 0 and self.charlst[i-1] != '\\':
        #         continue 
        #     if char == '[':
        #         brk = Bracket(i, None, 'cond')
        #         conds.append(brk)
        #         indices[i] = brk 
        #     elif char == '$':
        #         if exprs[-1].get('end') is None:
        #             exprs[-1].end = i
        #         else:
        #             brk = Bracket(i, None, 'expr')
        #             exprs.append(brk)
        #             indices[i] = brk
        #     elif char == '(':
        #         j = i
        #         # go backwards until you find a space
        #         while self.charlst[j] != ' ':
        #             j -= 1
        #         j += 1

        #         funcname = ''.join(self.charlst[j:i])
        #         if funcname not in self.funcs:
        #             ignore_closing_paren = True
        #             continue 
        #         brk = Bracket(i, None, 'func', funcname)
        #         funcs.append(brk)
        #         indices[i] = brk
        #     elif char == ']':
        #         conds[-1].end = i
        #     elif char == ')':
        #         if not ignore_closing_paren:
        #             funcs[-1].end = i
        #         else:
        #             ignore_closing_paren = False

        def ordered_eval(string):
            newstr = ''
            i = 0
            while i < len(string):
                if i > 0 and string[i-1] == '\\':
                    newstr += string[i]
                    i += 1
                    continue
                if string[i] == '[':
                    # find the closing bracket
                    counter = 0
                    j = i+1

                    found = False
                    while j < len(string):
                        if string[j] == '[':
                            counter += 1
                        elif string[j] == ']':
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
                        newstr += inside[match.end():]

                    i += j - i + 1
                elif string[i] == '(':
                    k = i-1
                    while k > 0 and string[k] != ' ':
                        k -= 1
                    funcname = string[k+1:i]
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
                    newstr += str(repl)

                    i += j - i + 1
                elif string[i] == '$':
                    # find next $ 
                    j = i+1
                    found = False 

                    while j < len(string):
                        if string[j] == '$':
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
                    newstr += str(repl)
                    i += j - i + 1
                elif string[i] == '<':
                    if i >= len(string) - 2 or string[i+1].lower() != 's' or string[i+2] != '>':
                        newstr += string[i]
                        i += 1
                        continue
                    
                    j = i+3
                    found = False
                    while j < len(string) - 3:
                        if string[j:j+4].lower() == '</s>':
                            found = True
                            break
                        j += 1

                    print(string) 
                    print('\n')
                    if not found:
                        raise UnmatchedBracket(f'Unmatched bracket: <s>')

                    def inner():
                        updates = '' 
                        for name, val in self.vars.items():
                            exec(f'{name} = {val}')
                        exec(string[i+3:j])
                        g = globals()
                        for varname in updates.split():
                            if varname in g:
                                self.vars[varname] = g[varname]
                    inner()
                    i += j - i + 4
                elif string[i] == '{':
                    j = i+1
                    while j < len(string) and string[j] != '}':
                        j += 1
                    varname = string[i+1:j]
                    if varname in self.vars_builtin:
                        repl = self.vars_builtin[varname]
                    elif varname in self.vars:
                        repl = self.vars[varname]
                    else:
                        repl = ''
                    newstr += str(repl)
                    i += j - i + 1
                else:
                    newstr += string[i]
                    i += 1

            return newstr
        
        return ordered_eval(text)

        # def ordered_eval(start_i, end_i):
        #     # recursively evaluate the string
        #     newstr = ''
        #     i = start_i 
        #     while i < end_i:
        #         if i not in indices:
        #             newstr += self.charlst[i]
        #             continue 
        #         brk = indices[i]
        #         if brk.brktype == 'script':
        #             def inner():
        #                 updates = '' 
        #                 exec(self.text[brk.beg:brk.end+1])
        #                 g = globals()
        #                 for varname in updates.split():
        #                     if varname in g:
        #                         self.vars[varname] = g[varname]
        #             inner()
        #             i += brk.end - brk.beg + 1
        #             continue 
        #         elif brk.brktype == 'cond':
                     



            




