from discord.ext import commands 
import asyncio
import json 
from discord import ui 
from discord.utils import escape_markdown
from embed_editor.editor import EmbedEditor
import discord 
from lunascript import ScriptContext, LunaScript, LunaScriptParser, clean 
import inspect 
import importlib 


class Tools(commands.Cog, description='storchs tools'):
    
    def __init__(self, bot):
        self.bot = bot 
        self.bot.layouts = {}

    async def cog_load(self):
        with open('vars.json') as f:
            self.bot.vars = json.load(f)
        
        rows = await self.bot.db.fetch('select * from layouts')
        self.bot.layouts = {row['name']: (row['content'], row['embed']) for row in rows}
    
    async def cog_unload(self):
        with open('vars.json', 'w') as f:
            json.dump(self.bot.vars, f, indent=4)

    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator or ctx.author.id == self.bot.owner_id

    @commands.command()
    async def buildembed(self, ctx):
        view = EmbedEditor(self.bot, ctx.author, timeout=None)
        await ctx.send('Please hit the **Submit** button when you\'re ready!', view=view)
        await view.wait()
        if view.ready:
            await ctx.send(embed=view.current_embed)
        
    @commands.command()
    async def showfuncs(self, ctx):
        ls = ScriptContext.from_ctx(ctx)
        embed = discord.Embed(title='LunaScript Functions', color=0xcab7ff)
        for names, func in ls.funcs_tuples.items():
            sig = inspect.signature(func)
            embed.add_field(name=names, value=func.__doc__ + f'\n\nUsage: {names[0]}{sig}', inline=False)
        # make a view with a dropdown to view the magicfuncs 
        await ctx.send(embed=embed)
    
    @commands.command()
    async def addvar(self, ctx, name, *, value):
        value = clean(value) 
        self.bot.vars[name] = value 
        await ctx.send('Done!') 
    
    @commands.command()
    async def reloadmodules(self, ctx):
        modules = ['lunascript', 'utils']
        for module in modules:
            module = __import__(module)
            importlib.reload(module)
        await ctx.send('Reloaded modules')
            
    @commands.command()
    async def showvars(self, ctx):
        ls = ScriptContext.from_ctx(ctx)
        embed = discord.Embed(title='LunaScript Variables', color=0xcab7ff)
        for names, func in ls.vars_builtin_tuples.items():
            names = ', '.join(names)
            embed.add_field(name=names, value=func.__doc__ + f'\n\nExample: {func()}', inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def lseval(self, ctx, *, string):
        parser = LunaScriptParser(ScriptContext.from_ctx(ctx))
        await ctx.send(await parser.parse(string))

    @commands.command()
    async def setlayout(self, ctx, *, name):
        temp = await ctx.send('Enter the text portion of the layout, or `skip` to skip.')
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=300)
        except asyncio.TimeoutError:
            await temp.delete()
            return 
        
        if msg.content.lower() == 'skip':
            text = None
            prompt = 'Enter the name of the layout\'s embed.'
        else:
            text = msg.content
            prompt = 'Enter the name of the layout\'s embed, or `skip` to skip.'
        
        temp = await ctx.send(prompt)
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            await temp.delete()
            return
        
        if text is not None and msg.content.lower() == 'skip':
            embed = None
        else:
            query = 'select name from embeds where name = ?'
            x = await self.bot.db.fetchval(query, msg.content.lower())
            if not x:
                await ctx.send('There is no embed with that name.', ephemeral=True)
                return
            embed = msg.content.lower()
        
        query = 'insert into layouts (name, content, embed) values (?, ?, ?) on conflict (name) do update set content = ?, embed = ?'
        await self.bot.db.execute(query, name.lower(), text, embed, text, embed)
        self.bot.layouts[name.lower()] = (text, embed)
        await ctx.send(f'Set the layout `{name.lower()}`!')

    @commands.command()
    async def viewlayout(self, ctx, *, name):
        if name.lower() not in self.bot.layouts:
            await ctx.send('There is no layout with that name.', ephemeral=True)
            return
        text, embed = self.bot.layouts[name.lower()]
        embed = self.bot.embeds[embed]
        
        ls = LunaScript(ctx, text, embed)
        await ls.send()
    
    @commands.command()
    async def viewrawlayout(self, ctx, *, name):
        if name.lower() not in self.bot.layouts:
            await ctx.send('There is no layout with that name.', ephemeral=True)
            return
        text, embed = self.bot.layouts[name.lower()]
        embed = self.bot.embeds[embed]
        await ctx.send(text, embed=embed)

    @commands.command()
    async def grabembed(self, ctx, url):
        tokens = url.split('/')
        channel_id = int(tokens[5])
        message_id = int(tokens[6])
        channel = self.bot.get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        embed = message.embeds[0].to_dict()

        # if 'footer' in embed:
            # embed.pop('footer')
            
        data = json.dumps(embed, indent=4)
        await ctx.send(f'```json\n{data}```')

    @commands.command()
    async def grabbuttonemoji(self, ctx, url):
        tokens = url.split('/')
        channel_id = int(tokens[5])
        message_id = int(tokens[6])
        channel = self.bot.get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        view = ui.View.from_message(message)
        await ctx.send(escape_markdown(str(view.children[0].emoji)))

async def setup(bot):
    await bot.add_cog(Tools(bot))