from discord.ext import commands, tasks 
import json 
from discord import app_commands
import discord 
from time import time as rn 
import datetime 
from utils.converters import TimeConverter 
import asyncio 


async def task(bot, channel, text, embed, interval, lastsent, name):
    sincelast = rn() - lastsent

    if sincelast < interval:
        await asyncio.sleep(interval - sincelast)
    while True:
        await channel.send(text, embed=embed)
        query = 'UPDATE ams SET lastsent = ? WHERE name = ?'
        await bot.db.execute(query, rn(), name) 
        await asyncio.sleep(interval)
        

class Automessages(commands.Cog):

    def __init__(self, bot):
        self.bot = bot 
        self.tasks = {} 

    async def cog_load(self):
        query = 'SELECT channel_id, text, embed, interval, lastsent, name FROM ams'
        rows = await self.bot.db.fetch(query)
        for row in rows:
            interval = row[3] 
            text = row[1]
            embed = row[2]
            if embed is not None:
                embed = discord.Embed.from_dict(json.loads(embed))
            channel = self.bot.get_channel(row[0])
            lastsent = row[4]
            name = row[5]
            
            taskobj = self.bot.loop.create_task(task(self.bot, channel, text, embed, interval, lastsent, name))
            self.tasks[name] = taskobj 

    async def cog_unload(self):
        for task in self.tasks.values():
            task.cancel() 

    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator or ctx.author.id == self.bot.owner_id
    
    @commands.hybrid_command()
    @app_commands.default_permissions()
    @app_commands.describe(name='a name for the automessage', channel='the channel to send the messages in', time='the interval')
    async def addam(self, ctx, name: str, channel: discord.TextChannel, time: TimeConverter):
        if time is None:
            return 

        name = name.lower()
        query = 'SELECT id FROM ams WHERE name = ?'
        val = await self.bot.db.fetchval(query, name)
        if val is not None:
            return await ctx.send('There is already an automessage under that name.', ephemeral=True) 
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel 
        
        await ctx.send("Please type the text component of the automessage. Type `skip` to skip this step.")
        resp = await self.bot.wait_for('message', check=check)
        if resp.content.lower() == 'skip':
            text = None 
        else:
            text = resp.content
        
        if text is None: 
            # has to choose embed

            await ctx.send("Please type the name of the embed you would like to send")
            while True:
                resp = await self.bot.wait_for('message', check=check)
                embedname = resp.content.lower()

                query = 'SELECT embed FROM embeds WHERE name = ?'
                val = await self.bot.db.fetchval(query, embedname)
                if val is None:
                    await ctx.send('No embed with that name found. Please try another name.')
                else:
                    embedjson = val 
                    break 
        else:

            await ctx.send("Please type the name of the embed you would like to send, or type `skip`.")

            while True:
                resp = await self.bot.wait_for('message', check=check)
                embedname = resp.content.lower()

                if embedname == 'skip':
                    embedjson = None 
                    break 

                query = 'SELECT embed FROM embeds WHERE name = ?'
                val = await self.bot.db.fetchval(query, embedname)
                if val is None:
                    await ctx.send('No embed with that name found. Please try another name.')
                else:
                    embedjson = val 
                    break 
        
        if embedjson is not None:
            embed = discord.Embed.from_dict(json.loads(embedjson)) 
        else:
            embed = None 

        taskobj = self.bot.loop.create_task(task(self.bot, channel, text, embed, time, 0, name))
        self.tasks[name] = taskobj 
        # msg = await channel.send(None, embed=realembed)
        await ctx.send(f'Made your automessage! See it in {channel.mention}')

        query = 'INSERT INTO ams (name, channel_id, interval, text, embed, lastsent) VALUES (?, ?, ?, ?, ?, ?)'
        await self.bot.db.execute(query, name, channel.id, time, text, embedjson, rn())

 
    @commands.hybrid_command()
    @app_commands.default_permissions()
    @app_commands.describe(name='the name for the automessage') 
    async def removeam(self, ctx, *, name: str):
        name = name.lower() 
        query = 'SELECT id FROM ams WHERE name = ?'
        val = await self.bot.db.fetchval(query, name)
        if val is None:
            return await ctx.send('No automessage under that name.', ephemeral=True)
        task = self.tasks.pop(name)
        task.cancel()
        query = 'DELETE FROM ams WHERE name = ?'
        await self.bot.db.execute(query, name)
        await ctx.send('Deleted your automessage!', ephemeral=True)
    
    @commands.hybrid_command()
    @app_commands.default_permissions()
    async def listams(self, ctx):
        query = 'SELECT name, channel_id FROM ams'
        rows = await self.bot.db.fetch(query)
        if not rows:
            return await ctx.send('No automessages found.')
        embed = discord.Embed(color=0xcab7ff, title='Automessages')
        fields = []
        for row in rows:
            channel = self.bot.get_channel(row[1])
            fields.append(f'`row[0]` in {channel.mention}')
        embed.description = '\n'.join(fields)
        await ctx.send(embed=embed)


        
async def setup(bot):
    await bot.add_cog(Automessages(bot))
