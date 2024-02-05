from discord.ext import commands
from discord.ext.commands.context import Context 
from embed_editor.editor import EmbedEditor
import json 
import discord 
from discord import app_commands 


def fill_embed(embed, var, repl):
    var = '{' + str(var) + '}'
    repl = str(repl)

    if embed.title is not None:
        embed.title = embed.title.replace(var, repl)
    if embed.description is not None:
        embed.description = embed.description.replace(var, repl)
    if embed.footer.text is not None:
        embed.footer.text = embed.footer.text.replace(var, repl)
    if embed.author.name is not None:
        embed.author.name = embed.author.name.replace(var, repl)
    for field in embed.fields:
        field.name = field.name.replace(var, repl)
        field.value = field.value.replace(var, repl)
    
    return embed

class Embeds(commands.Cog, description='Create, save, and edit your own embeds.'):

    def __init__(self, bot):
        self.bot = bot 
        self.bot.embeds = {}

    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator or ctx.author.id == self.bot.owner_id
    
    async def cog_load(self):
        query = 'SELECT name, embed FROM embeds'
        rows = await self.bot.db.fetch(query)
        for row in rows:
            self.bot.embeds[row['name']] = discord.Embed.from_dict(json.loads(row['embed']))

    
    @commands.hybrid_group()
    @app_commands.default_permissions()
    async def embed(self, ctx):
        """No purpose, just shows help"""
        await ctx.send_help(ctx.command)
    
    @embed.command()
    async def fromjson(self, ctx, name, *, jsonstr):
        """Create an embed from a json string"""
        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = 'SELECT id FROM embeds WHERE name = ?'
                await cur.execute(query, (name.lower(),))
                x = await cur.fetchone()
                if x:
                    await ctx.send('There is already an embed with that name!', ephemeral=True)
                    return 

        try:
            embed = discord.Embed.from_dict(json.loads(jsonstr))
        except json.JSONDecodeError:
            await ctx.send('That is not valid json.', ephemeral=True)
            return 
        data = json.dumps(embed.to_dict())
        async with self.bot.pool.acquire() as conn:
            query = 'INSERT INTO embeds (creator_id, name, embed) VALUES (?, ?, ?)'
            await conn.execute(query, (ctx.author.id, name.lower(), data))
            await conn.commit()
            self.bot.embeds['json'] = discord.Embed.from_dict(json.loads(data))

        await ctx.send(f'Added your embed {name}!')

    @embed.command()
    @app_commands.default_permissions()
    async def create(self, ctx, *, name):
        """Create an embed with LunaBot"""
        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = 'SELECT id FROM embeds WHERE name = ?'
                await cur.execute(query, (name.lower(),))
                x = await cur.fetchone()
                if x:
                    await ctx.send('There is already an embed with that name!', ephemeral=True)
                    return 
                
                
        view = EmbedEditor(self.bot, ctx.author, timeout=None)
        await ctx.send(view=view, ephemeral=True)
        await view.wait()
        if view.ready:
            data = json.dumps(view.current_embed.to_dict())
            async with self.bot.pool.acquire() as conn:
                query = 'INSERT INTO embeds (creator_id, name, embed) VALUES (?, ?, ?)'
                await conn.execute(query, (ctx.author.id, name.lower(), data))
                await conn.commit()
                self.bot.embeds[name.lower()] = discord.Embed.from_dict(json.loads(data))

            await ctx.send(f'Added your embed `{name.lower()}`!')
    
    @embed.command()
    @app_commands.default_permissions()
    async def edit(self, ctx, *, name):
    
        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = 'SELECT embed FROM embeds WHERE name = ? AND creator_id = ?'
                await cur.execute(query, (name.lower(), ctx.author.id))
                x = await cur.fetchone()
                if not x:
                    await ctx.send('You do not own an embed with that name.', ephemeral=True)
                    return 
                
        embed = discord.Embed.from_dict(json.loads(x[0]))
        view = EmbedEditor(self.bot, ctx.author, timeout=None, embed=embed)
        await ctx.send(embed=embed, view=view, ephemeral=True)
        await view.wait()
        if view.ready:
            data = json.dumps(view.current_embed.to_dict())
            async with self.bot.pool.acquire() as conn:
                query = 'UPDATE embeds SET embed = ? WHERE name = ?'
                await conn.execute(query, (data, name.lower()))
                await conn.commit()
                self.bot.embeds[name.lower()] = discord.Embed.from_dict(json.loads(data))

            await ctx.send(f'Edited the embed `{name.lower()}`!')
    
    @embed.command()
    @app_commands.default_permissions()
    async def delete(self, ctx, *, name):
        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                if not ctx.author.guild_permissions.administrator:
                    query = 'SELECT embed FROM embeds WHERE name = ? AND creator_id = ?'
                    await cur.execute(query, (name.lower(), ctx.author.id))
                    x = await cur.fetchone()
                    if not x:
                        await ctx.send('You do not own an embed with that name.', ephemeral=True)
                        return 
                else:
                    query = 'SELECT embed FROM embeds WHERE name = ?'
                    await cur.execute(query, (name.lower(),))
                    x = await cur.fetchone()
                    if not x:
                        await ctx.send('There is no embed with that name.', ephemeral=True)
                        return 
                
        async with self.bot.pool.acquire() as conn:
            query = 'DELETE FROM embeds WHERE name = ?'
            await conn.execute(query, (name.lower(),))
            await conn.commit()
            self.bot.embeds.pop(name.lower(), None)

        await ctx.send(f'Deleted the embed `{name.lower()}`!')
        
    @embed.command()
    @app_commands.default_permissions()
    async def show(self, ctx, *, name):
        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = 'SELECT embed FROM embeds WHERE name = ?'
                await cur.execute(query, (name.lower(),))
                x = await cur.fetchone()
                if not x:
                    await ctx.send('You do not own an embed with that name.', ephemeral=True)
                    return 
    
                embed = discord.Embed.from_dict(json.loads(x[0]))
                await ctx.send(embed=embed)
    
    @embed.command(name='list')
    @app_commands.default_permissions()
    async def _list(self, ctx):
        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = 'SELECT name FROM embeds'
                await cur.execute(query)
                x = await cur.fetchall()

        if len(x) == 0:
            await ctx.send('You have created no embeds.', ephemeral=True)
            return 
    
        lazy = '\n'.join(f'`{row[0]}`' for row in x)
        embed = discord.Embed(
            color=0xcab7ff,
            title='Your Embeds',
            description=lazy
        )
        await ctx.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Embeds(bot))


        



