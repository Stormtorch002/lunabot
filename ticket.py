import json 
import discord 
from discord.ext import commands 
from discord import ui 
import time 
import asqlite
import asyncio 
from datetime import timedelta, datetime

with open('data.json') as f:
    data = json.load(f)


# ticket_cds = {}
# tickets = []

class Ticket:
    def __init__(self, opener, timestamp, archive_id):
        self.opener = opener
        self.timestamp = timestamp 
        self.id = None
        self.channel = None
        self.archive_id = archive_id
    
     
    

class CloseReason(ui.Modal, title='Close'):
    reason = ui.TextInput(
        label='Reason', 
        placeholder='Reason for closing the ticket, e.g. "Resolved"',
        max_length=1024
    )

    async def on_submit(self, inter):
        await inter.response.send_message('Ticket closed, deleting channel in 5 seconds...')

    

class CloseView(ui.View):
    def __init__(self, ticket_id, channel, opener_id, timestamp, archive_id):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        self.channel = channel 
        self.opener_id = opener_id 
        self.timestamp = timestamp
        self.archive_id = archive_id
        self.close_without_reason.custom_id = f'ticket-noreason-{ticket_id}'
        self.close_with_reason.custom_id = f'ticket-reason-{ticket_id}'

    async def close(self, inter, reason):
        await self.channel.delete()
        async with inter.client.pool.acquire() as conn:
            query = 'DELETE FROM actickets WHERE ticket_id = ?'
            await conn.execute(query, (self.ticket_id,))
            await conn.commit()

        embed = discord.Embed(
            title='Ticket Closed',
            color=0xcab7ff,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name='Ticket ID', value=str(self.ticket_id))
        embed.add_field(name='Opened By', value=f'<@!{self.opener_id}>')
        embed.add_field(name='Closed By', value=inter.user.mention)
        embed.add_field(name='Open Time', value=discord.utils.format_dt(self.timestamp))
        embed.add_field(name='Reason', value=reason, inline=False)
        archive = inter.client.get_channel(self.archive_id)
        await archive.send(embed=embed)
        
    @ui.button(label='Close', style=discord.ButtonStyle.red, emoji='\U0001f512')
    async def close_without_reason(self, inter, button):
        await inter.response.send_message('Ticket closed, deleting channel in 5 seconds...')
        await asyncio.sleep(5)
        await self.close(inter, "No reason given")
    
    @ui.button(label='Close With Reason', style=discord.ButtonStyle.red, emoji='\U0001f512', row=1)
    async def close_with_reason(self, inter, button):
        modal = CloseReason()
        await inter.response.send_modal(modal)
        await modal.wait()
        await asyncio.sleep(5)
        await self.close(inter, str(modal.reason))



class TicketView(ui.View):

    def __init__(
            self, 
            bot, 
            channel_id, 
            custom_id, 
            emoji, 
            required_role_id,
            missing_role_message,
            initial_wait_message,
            cooldown, 
            cooldown_message,
            embed1, 
            embed2, 
            archive_id, 
            staff_id,
        ):
        self.bot = bot
        self.emoji = emoji
        self.custom_id = custom_id 
        self.channel_id = channel_id
        self.required_role_id = required_role_id
        self.missing_role_message = missing_role_message
        self.initial_wait_message = initial_wait_message
        self.cooldown = cooldown 
        self.cooldown_message = cooldown_message
        self.embed1 = discord.Embed.from_dict(embed1)
        self.embed2 = discord.Embed.from_dict(embed2)
        self.archive_id = archive_id
        self.staff_id = staff_id

        # emoji = self.bot.get_emoji(924048498477891614)
        btn_text = "❀﹒﹒Click me!﹒﹒❀"
        btn = ui.Button(
            custom_id=custom_id, 
            label=btn_text, 
            style=discord.ButtonStyle.blurple, 
            emoji=self.emoji
        )

        async def callback(inter):
            await inter.response.defer()
            ticket = await self.create_ticket(inter)
            embed = discord.Embed(
                title='Ticket',
                color=0xcab7ff,
                description=f'Opened a new ticket: {ticket.channel.mention}'
            )
            await inter.followup.send(embed=embed, ephemeral=True)

        btn.callback = callback 

        super().__init__(timeout=None)
        self.add_item(btn)
        
    async def create_ticket(self, inter):
        ticket = Ticket(inter.user, discord.utils.utcnow(), self.archive_id)
        channel = await self.create_channel(inter, ticket)
        role = inter.guild.get_role(self.staff_id)
        temp = await channel.send(f'{role.mention} {inter.user.mention}')
        # temp = await channel.send(inter.user.mention)
        view = CloseView(ticket.id, ticket.channel, ticket.opener.id, ticket.timestamp, ticket.archive_id)
        async with self.bot.pool.acquire() as conn:
            query = 'INSERT INTO actickets (ticket_id, channel_id, opener_id, timestamp, archive_id) VALUES (?, ?, ?, ?, ?)'
            await conn.execute(query, (ticket.id, ticket.channel.id, ticket.opener.id, ticket.timestamp.timestamp(), ticket.archive_id))
            await conn.commit()
        
        # inter.client.add_view(view)  
        await channel.send(view=view, embed=self.embed2)
        await temp.delete()
        return ticket 

    async def create_channel(self, inter, ticket):
        async with inter.client.pool.acquire() as conn:
            async with conn.cursor() as cur:
                query = 'UPDATE counter SET num = num + 1'
                await cur.execute(query)
                await conn.commit()
            async with conn.cursor() as cur:
                query = 'SELECT num FROM counter'
                await cur.execute(query)
                row = await cur.fetchone()
                (ticket_id,) = row
                self.id = ticket_id

        ticket.id = ticket_id
        archive = inter.client.get_channel(self.archive_id)
        staffrole = inter.guild.get_role(self.staff_id)
        overwrites = {
            inter.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            inter.user: discord.PermissionOverwrite(view_channel=True),
            staffrole: discord.PermissionOverwrite(view_channel=True)
        }
        ticket.channel = await archive.category.create_text_channel(name=f'ticket-{ticket_id}', overwrites=overwrites)
        return ticket.channel
    
    async def interaction_check(self, inter):
        # if inter.user.id == STORCH_ID:
        #     return True 
        
        if self.required_role_id:
            if self.required_role_id not in [r.id for r in inter.user.roles]:
                await inter.response.send_message(self.missing_role_message, ephemeral=True)
                return 
            
        async with self.bot.pool.acquire() as conn:
            query = 'SELECT end_time, reason FROM cooldowns WHERE custom_id = ? AND user_id = ? ORDER BY end_time DESC'
            async with conn.cursor() as cursor:
                await cursor.execute(query, (self.custom_id, inter.user.id))
                row = await cursor.fetchone()
            
            if row is None or row[0] - time.time() < 0:
                query = 'INSERT INTO cooldowns (custom_id, user_id, end_time) VALUES (?, ?, ?)'
                await conn.execute(query, (self.custom_id, inter.user.id, int(time.time() + self.cooldown)))
                await conn.commit()
                return True
            else:
                dt = discord.utils.utcnow() + timedelta(seconds=row[0] - time.time())
                md = discord.utils.format_dt(dt, 'R')
                if row[1]:
                    msg = self.initial_wait_message
                else:
                    if self.cooldown_message is None:
                        msg = "♡﹒﹒**Psst!** Please slow down a bit; there is a __1 minute__ cooldown to prevent spam. Please try again (time thingy)! <a:Lumi_heart_bounce:917958025195696169> __ __✿__ __❀__ __"
                    else:
                        msg = self.cooldown_message 
                msg = msg.replace('(time thingy)', md)
                await inter.response.send_message(
                    msg,
                    ephemeral=True
                )
                return False 


STORCH_ID = 718475543061987329

class TicketCog(commands.Cog, name='Tickets', description='a few sketchy admin-only sketchy commands'):

    def __init__(self, bot):
        self.bot = bot 

    async def cog_load(self):
        self.bot.pool = self.bot.db.pool

        for guild in data:
            archive_id = guild['archive id']
            staff_id = guild['staff id']
            for ticket in guild['tickets']:
                self.bot.add_view(TicketView(
                    self.bot, 
                    ticket['channel id'], 
                    ticket['custom id'], 
                    ticket.get('emoji'),
                    ticket.get('required role id'),
                    ticket.get('missing role message'),
                    ticket.get('initial wait message'),
                    ticket['cooldown'],
                    ticket.get('cooldown_message'),
                    ticket['embed 1'],
                    ticket['embed 2'],
                    archive_id,
                    staff_id
                ))
        
        async with self.bot.pool.acquire() as conn:
            query = 'SELECT ticket_id, channel_id, opener_id, timestamp, archive_id FROM actickets'
            async with conn.cursor() as cur:
                await cur.execute(query)
                rows = await cur.fetchall()
                for row in rows:
                    close = CloseView(row[0], self.bot.get_channel(row[1]), row[2], datetime.fromtimestamp(row[3]), row[4])
                    self.bot.add_view(close)

    async def cog_unload(self):
        await self.bot.pool.close()

    async def cog_check(self, ctx):
        return ctx.author.id == STORCH_ID or ctx.author.guild_permissions.administrator

    @commands.command()
    async def sendembed(self, ctx, channel: discord.TextChannel):
        for view in self.bot.persistent_views:
            if view.channel_id == channel.id:
                embed = view.embed1
                await channel.send(embed=embed, view=view)
                await ctx.send('ok')
                return 
        await ctx.send('i dont have a ticket prepared for that channel yet, pls contact storch')
        
    @commands.command()
    async def giverole(self, ctx, member: discord.Member, role: discord.Role):
        for view in self.bot.persistent_views:
            if view.required_role_id == role.id:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    await ctx.send('I couldnt give that member the role, make sure im not being permission hiearchyd')
                    return 
                
                async with self.bot.pool.acquire() as conn:
                    query = 'INSERT INTO cooldowns (custom_id, user_id, end_time, reason) VALUES (?, ?, ?, ?)'
                    await conn.execute(query, (view.custom_id, member.id, int(time.time() + view.cooldown), 'initial wait'))
                    await conn.commit()
                
                channel = self.bot.get_channel(view.channel_id)
                md = discord.utils.format_dt(discord.utils.utcnow() + timedelta(seconds=view.cooldown), 'd')
                await ctx.send(f'I gave {member.mention} the role; they can apply in {channel.mention} on {md}')
                return 
        await ctx.send('that role isnt required for any tickets')

async def setup(bot):
    await bot.add_cog(TicketCog(bot))