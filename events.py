from typing import Literal
import logging
from discord.ext import commands 
import json 
import discord
from embed_editor.editor import EmbedEditor
from discord import ui 
from textwrap import dedent
from num2words import num2words
import asyncio 
import time 
from discord import app_commands 

# BOOSTER_ROLE_ID = 913086743035658292
BOOSTER_ROLE_ID = 953441647507673088
FREE_OFFERS_CHANNEL_ID = 1127014412432183347


class Events(commands.Cog, description='Manage join, leave, boost, and birthday messages'):

    def __init__(self, bot):
        self.bot = bot 
        with open('events.json') as f:
            self.events = json.load(f)
        self.rm_role_tasks = {}

    async def rm_role(self, row):
        await asyncio.sleep(row[3] - time.time())
        guild = self.bot.get_guild(row[1])
        role = guild.get_role(row[2])
        member = guild.get_member(row[0])
        if member:
            await member.remove_roles(role)
            async with self.bot.pool.acquire() as conn:
                query = 'DELETE FROM rmroles WHERE id = ?'
                await conn.execute(query, (row[4],))
                await conn.commit()
        self.rm_role_tasks.pop(row[4])

    async def cog_load(self):
        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = 'SELECT user_id, guild_id, role_id, rm_time, id FROM rmroles'
                await cur.execute(query)
                x = await cur.fetchall()
                for row in x:
                    task = self.bot.loop.create_task(self.rm_role(row))
                    self.rm_role_tasks[row[4]] = task
        
                    
    async def cog_unload(self):
        for task in self.rm_role_tasks.values():
            task.cancel()

    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator or ctx.author.id == self.bot.owner_id
    
    async def send_embed(self, member, repl, event, bday_role=None):
        if event == 'birthday':
            await member.add_roles(bday_role)
            
            async with self.bot.pool.acquire() as conn:
                rm_time = time.time() + 7

                query = 'INSERT INTO rmroles (user_id, guild_id, role_id, rm_time) VALUES (?,?,?,?) ON CONFLICT(user_id, role_id) DO UPDATE SET rm_time = ?'
                await conn.execute(query, (member.id, member.guild.id, bday_role.id, rm_time, rm_time))
                await conn.commit()
                async with conn.cursor() as cur:
                    await cur.execute('SELECT user_id, guild_id, role_id, rm_time, id FROM rmroles WHERE user_id = ? AND role_id = ?', (member.id, bday_role.id))
                    row = await cur.fetchone()
                    task = self.bot.loop.create_task(self.rm_role(row))
                    self.rm_role_tasks[row[4]] = task

        data = self.events[str(member.guild.id)][event]
        embeddict = data.get('embed')
        text = data.get('text')
        if text:
            for x, y in repl.items():
                text = text.replace(x, str(y))
        if embeddict:
            js = json.dumps(embeddict)
            for x, y in repl.items():
                js = js.replace(x, str(y))
            embed = discord.Embed.from_dict(json.loads(js))
        else:
            embed = None
        channel = self.bot.get_channel(data['channel_id'])
        await channel.send(text, embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == FREE_OFFERS_CHANNEL_ID:
            await message.add_reaction('<a:LCM_mail:1151561338317983966>')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = 'SELECT role_id FROM rmroles WHERE user_id = ?'
                await cur.execute(query, (member.id,))
                row = await cur.fetchone()
                if row:
                    role = member.guild.get_role(row[0])
                    await member.add_roles(role)
                    
        if str(member.guild.id) not in self.events:
            return 
        if 'welcome' not in self.events[str(member.guild.id)]:
            return 
        count = len(member.guild.members)
        repl = {
            '{name}': member.display_name,
            '{mention}': member.mention,
            '{username}': member.name,
            '{number}': count,
            '{ordinal}': num2words(count, to='ordinal_num')
        }
        await self.send_embed(member, repl, 'welcome')
    
    @commands.Cog.listener()
    async def on_member_leave(self, member):
        if str(member.guild.id) not in self.events:
            return 
        if 'goodbye' not in self.events[str(member.guild.id)]:
            return 
        
        count = len(member.guild.members)
        repl = {
            '{name}': member.display_name,
            '{mention}': member.mention,
            '{username}': member.name,
            '{number}': count,
            '{ordinal}': num2words(count, to='ordinal_num')
        }
        await self.send_embed(member, repl, 'goodbye')
    
    @commands.command()
    async def boosttest(self, ctx):
        booster_role = ctx.guild.get_role(BOOSTER_ROLE_ID)
        if booster_role not in ctx.author.roles:
            await ctx.author.add_roles(booster_role)
        else:
            await ctx.author.remove_roles(booster_role)
        await ctx.send(':white_check_mark:')

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        booster_role = before.guild.get_role(BOOSTER_ROLE_ID)
        logging.info('member update')

        if booster_role not in before.roles and booster_role in after.roles:
            logging.info(f'{after} boosted {after.guild}')
            member = after

            if str(member.guild.id) not in self.events:
                return 
            if 'boost' not in self.events[str(member.guild.id)]:
                return 
        
            count = member.guild.premium_subscription_count
            repl = {
                '{name}': member.display_name,
                '{mention}': member.mention,
                '{username}': member.name,
                '{number}': count,
                '{ordinal}': num2words(count, to='ordinal_num')
            }
            await self.send_embed(member, repl, 'boost')

    @commands.hybrid_command(name='set-event-text')
    @app_commands.default_permissions()
    async def settext(self, ctx, event: Literal['welcome', 'goodbye', 'boost', 'birthday'], channel: discord.TextChannel, *, text: str):
        """Sets the text for welcome/leave/boost/birthday messages."""

        if str(ctx.guild.id) not in self.events:
            self.events[str(ctx.guild.id)] = {}
        if event not in self.events[str(ctx.guild.id)]:
            self.events[str(ctx.guild.id)][event] = {
                'channel_id': channel.id,
                'text': text
            }
        else:
            self.events[str(ctx.guild.id)][event]['text'] = text 
            self.events[str(ctx.guild.id)][event]['channel_id'] = channel.id 

        with open('events.json', 'w') as f:
            json.dump(self.events, f)
        await ctx.send(f'**{event}** message text set for {channel.mention}!', ephemeral=True)
            
    @commands.hybrid_command(name='set-event-embed')
    @app_commands.default_permissions()
    async def setembed(self, ctx, event: Literal['welcome', 'goodbye', 'boost', 'birthday'], channel: discord.TextChannel, *, name: str):
        """Sets an embed for welcome/leave/boost/birthday messages."""
        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = 'SELECT embed FROM embeds WHERE name = ? AND creator_id = ?'
                await cur.execute(query, (name.lower(), ctx.author.id,))
                x = await cur.fetchone()
        
        if not x:
            await ctx.send('You do not have an embed with that name.', ephemeral=True)
            return 

        async def ez(event, embed):
            if str(ctx.guild.id) not in self.events:
                self.events[str(ctx.guild.id)] = {}
            if event not in self.events[str(ctx.guild.id)]:
                self.events[str(ctx.guild.id)][event] = {
                    'channel_id': channel.id,
                    'embed': embed.to_dict()
                }
            else:
                self.events[str(ctx.guild.id)][event]['embed'] = embed.to_dict()
                self.events[str(ctx.guild.id)][event]['channel_id'] = channel.id 

            with open('events.json', 'w') as f:
                json.dump(self.events, f)
            await ctx.send(f'**{event}** message embed set for {channel.mention}!', ephemeral=True)
        await ez(event, discord.Embed.from_dict(json.loads(x[0])))

        # class View(ui.View):

        #     def __init__(self):
        #         super().__init__()
            
        #     async def interaction_check(self, inter):
        #         return inter.user.id == ctx.author.id 

        #     @discord.ui.select(
        #         options=[
        #             discord.SelectOption(label='welcome'),
        #             discord.SelectOption(label='goodbye'),
        #             discord.SelectOption(label='boost')
        #         ]
        #     )
        #     async def dropdown(self, inter, select):
        #         event = select.values[0]
        #         view2 = EmbedEditor(inter.client, inter.user, None)
        #         msg = f'''
        #         Please build your **{event}** embed using the builder.

        #         Possible placeholders:
        #         {{name}}: user's display name
        #         {{mention}}: user's mention
        #         {{username}}: user's username
        #         {{number}}: the amount of members/boosts (e.g. `member #{{number}}`)
        #         {{ordinal}}: the amount of members/boosts expressed as an ordinal (e.g. `you are the {{ordinal}} member`)
        #         '''
        #         await inter.response.send_message(dedent(msg), view=view2)
        #         await view2.wait()
        #         if view2.ready:
        #             await ez(event, view2.current_embed)
                
        # await ctx.send('Start by selecting which event to make this embed for:', view=View())

                
async def setup(bot):
    await bot.add_cog(Events(bot))


