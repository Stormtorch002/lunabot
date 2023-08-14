from discord.ext import commands 
from discord import ui
from embed_editor.editor import EmbedEditor
import discord 
import json 
import asyncio 
import re 
from discord.ext.commands import Greedy 
from typing import Union, Literal
from discord import Member, Role, TextChannel


class AutoResponder:

    def __init__(self, phrase, detection, guilds, wlusers, blusers, wlroles, blroles, wlchannels, blchannels, text, embed):
        self.phrase = phrase 
        self.detection = detection 

        self.guilds = json.loads(guilds) if guilds else []
        self.wlusers = json.loads(wlusers) if wlusers else []
        self.blusers = json.loads(blusers) if blusers else []
        self.wlroles = json.loads(wlroles) if wlroles else []
        self.blroles = json.loads(blroles) if blroles else []
        self.wlchannels = json.loads(wlchannels) if wlchannels else []
        self.blchannels = json.loads(blchannels) if blchannels else []
        self.text = text
        self.embed = json.loads(embed)
    

class AutoResponderCog(commands.Cog, name='Autoresponders', description="Autoresponder stuff (admin only)"):
    def __init__(self, bot):
        self.bot = bot 
        self.ars = []
    
    async def cog_load(self):
        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = 'SELECT * FROM ars'
                await cur.execute(query)
                rows = await cur.fetchall()

                for row in rows:
                    self.ars.append(
                        AutoResponder(*[row[i] for i in range(1, 12)])
                    )

    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator or await self.bot.is_owner(ctx.author)
    
    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot: 
            return 
        
        roleids = [r.id for r in msg.author.roles]
        for ar in self.ars:
            if msg.guild.id not in ar.guilds:
                continue 
            if ar.wlusers and msg.author.id not in ar.wlusers:
                continue 
            if ar.blusers and msg.author.id in ar.blusers:
                continue 
            if ar.wlroles and all(role not in roleids for role in ar.roles):
                continue 
            if ar.blroles and any(role in roleids for role in ar.roles):
                continue 
            if ar.wlchannels and msg.channel.id not in ar.wlchannel:
                continue 
            if ar.blchannels and msg.channel.id in ar.blchannels:
                continue 
            
            content = msg.content.lower()
            if ar.detection == 'any':
                if ar.phrase not in content:
                    continue 
            elif ar.detection == 'full':
                if ar.phrase != content:
                    continue 
            elif ar.detection == 'word':
                if ar.phrase not in content.split():
                    continue 
            elif ar.detection == 'regex':
                if not re.search(ar.phrase, msg.content, re.IGNORECASE):
                    continue 
            
            if ar.embed:
                embed = discord.Embed.from_dict(ar.embed)
            await msg.channel.send(ar.text, embed=embed)

    @commands.command()
    async def addar(self, ctx, *, phrase):
        """Adds an autoresponder to one or more servers."""

        if phrase.lower() in [ar.phrase for ar in self.ars]:
            await ctx.send('There is already an autoresponder for this phrase.')
            return 
        
        view = ui.View()
        select = ui.Select(
            options=[
                discord.SelectOption(label=i, value=j) 
                for i, j in [
                    ("match full message", "full"),
                    ("match any part of message", "any"),
                    ("match word in message", "word"),
                    ("regex", "regex")
                ]
            ]
        )
        choice = None
        async def callback(inter):
            nonlocal choice 
            if inter.user != ctx.author:
                return await inter.response.defer()
            await inter.response.delete_message()
            choice = inter.data['values'][0]
            view.stop()

        select.callback = callback 
        view.add_item(select)
        temp = await ctx.send("How would you like this phrase to be detected?", view=view)
        await view.wait()
        if choice is None:
            await temp.delete()
            return 
        
        view = ui.View()
        select = ui.Select(
            options=[
                discord.SelectOption(label=guild.name, value=guild.id) 
                for guild in self.bot.guilds
            ],
            max_values=len(self.bot.guilds),
        )
        guild_ids = []
        async def callback(inter):
            nonlocal guild_ids
            
            if inter.user != ctx.author:
                return await inter.response.defer()
            await inter.response.delete_message()
            guild_ids = inter.data['values']
            view.stop()

        select.callback = callback 
        view.add_item(select)
        temp = await ctx.send("Which servers would you like this autoresponder to be enabled in?", view=view)
        await view.wait()
        if len(guild_ids) == 0:
            await temp.delete()
            return 
        guild_ids = [int(guild_id) for guild_id in guild_ids]
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel 
        
        await ctx.send("Please type the text component of the autoresponse. Type `skip` to skip this step.")
        resp = await self.bot.wait_for('message', check=check)
        if resp.content.lower() == 'skip':
            text = None 
        else:
            text = resp.content

        view = EmbedEditor(self.bot, ctx.author, timeout=None)
        if text is None:
            await ctx.send("Please use the menu to create an embed.", view=view)
            await view.wait()
        else:
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'skip'
            
            await ctx.send("Please use the menu to create an embed, or type `skip` to skip.", view=view)
            task1 = self.bot.wait_for('message', check=check)
            task2 = view.wait()
            tasks = [task1, task2]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()

        if view.ready:
            embed = json.dumps(view.current_embed.to_dict())
        else:
            if text is None:
                return await ctx.send('Autoresponder cancelled.')
        self.ars.append(
            AutoResponder(phrase.lower(), choice, json.dumps(guild_ids), '[]', '[]', '[]', '[]', '[]', '[]', text, embed)
        )
        async with self.bot.pool.acquire() as conn:
            query = '''INSERT INTO ars (phrase, detection, guilds, message, embed)
                        VALUES (?, ?, ?, ?, ?)'''
            await conn.execute(query, (phrase.lower(), choice, json.dumps(guild_ids), text, embed))
            await conn.commit()
        await ctx.send('Successfully made autoresponder!')
        
    @commands.command()
    async def removear(self, ctx, *, phrase):
        """Removes an autoresponder."""
        for ar in self.ars:
            if ar.phrase == phrase.lower():
                self.ars.remove(ar)
                async with self.bot.pool.acquire() as conn:
                    query = '''DELETE FROM ars WHERE phrase = ?'''
                    await conn.execute(query, (phrase.lower(),))
                    await conn.commit()
                return await ctx.send('Successfully removed autoresponder.')
        await ctx.send('No autoresponder with that name.')
            
    @commands.command()
    async def addarwl(self, ctx, objects: Greedy[Union[Member, Role, TextChannel]], *, phrase):
        if len(objects) == 0:
            return await ctx.send("Please provide at least one member, role, or channel before the phrase")
        
        async with self.bot.pool.acquire() as conn:
            for ar in self.ars:
                if ar.phrase == phrase.lower():
                    embed = discord.Embed(title='Added the following to the whitelist', color=0xcab7ff)
                    ked = []
                    for obj in objects:
                        if isinstance(obj, Member):
                            if obj.id in ar.wlusers:
                                continue 
                            ar.wlusers.append(obj.id)
                            query = 'UPDATE ars SET wlusers = ? WHERE phrase = ?'
                            await conn.execute(query, (json.dumps(ar.wlusers), phrase))
                        elif isinstance(obj, Role):
                            if obj.id in ar.wlroles:
                                continue 
                            ar.wlroles.append(obj.id)
                            query = 'UPDATE ars SET wlroles = ? WHERE phrase = ?'
                            await conn.execute(query, (json.dumps(ar.wlroles), phrase))
                        else:
                            if obj.id in ar.wlchannels:
                                continue 
                            ar.wlchannels.append(obj.id)
                            query = 'UPDATE ars SET wlchannels = ? WHERE phrase = ?'
                            await conn.execute(query, (json.dumps(ar.wlchannels), phrase))
                        ked.append(obj.mention)
                    embed.description = '\n'.join(ked)
                    await ctx.send(embed=embed)

                    # remove blacklist
                    return 
        await ctx.send('No autoresponder with that name.')
    
    


async def setup(bot):
    await bot.add_cog(AutoResponderCog(bot))

