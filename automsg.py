from discord.ext import commands, tasks 
import json 
from discord import app_commands
import discord 
from time import time as rn 
import datetime 
from utils.converters import TimeConverter 
import asyncio 


async def task(channel, text, embed, interval, lastsent):
    sincelast = rn() - lastsent

    if sincelast < interval:
        await asyncio.sleep(interval - sincelast)
    while True:
        await channel.send(text, embed=embed)
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
            
            taskobj = self.bot.loop.create_task(task(channel, text, embed, interval, lastsent, name))
            self.tasks[name] = taskobj 

    async def cog_unload(self):
        for task in self.tasks.values():
            task.cancel() 

    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator or ctx.author.id == self.bot.STORCH_ID
    
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
                    embed = val 
                    break 
        else:

            await ctx.send("Please type the name of the embed you would like to send, or type `skip`.")

            while True:
                resp = await self.bot.wait_for('message', check=check)
                embedname = resp.content.lower()

                if embedname == 'skip':
                    embed = None 
                    break 

                query = 'SELECT embed FROM embeds WHERE name = ?'
                val = await self.bot.db.fetchval(query, embedname)
                if val is None:
                    await ctx.send('No embed with that name found. Please try another name.')
                else:
                    embed = val 
                    break 
        
        
        taskobj = self.bot.loop.create_task(task(channel, text, embed, time, 0, name))
        self.tasks[name] = taskobj 
        # msg = await channel.send(None, embed=realembed)
        await ctx.send(f'Made your automessage! See it in {channel.mention}')

        query = 'INSERT INTO ams (channel_id, interval, text, embed, lastsent) VALUES (?, ?, ?, ?, ?)'
        await self.bot.db.execute(query, channel.id, time, text, embed, rn())

 
    @commands.hybrid_command()
    @app_commands.default_permissions()
    @app_commands.describe(name='the name for the automessage') 
    async def removeam(self, ctx, *, name: str):
        name = name.lower() 
        query = 'SELECT id FROM automsg WHERE name = ?'
        val = await self.bot.db.fetchval(query, name)
        if val is None:
            return await ctx.send('No automessage under that name.', ephemeral=True)
        task = self.tasks.pop(name)
        task.cancel()
        query = 'DELETE FROM automsg WHERE name = ?'
        await self.bot.db.execute(query, name)
        await ctx.send('Deleted your automessage!', ephemeral=True)

        
async def setup(bot):
    await bot.add_cog(Automessages(bot))
