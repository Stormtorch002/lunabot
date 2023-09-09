from discord import app_commands 
from discord.ext import commands, tasks 
import discord 
import time 
import datetime 
from discord import ui
from discord import ButtonStyle
import json 
import textwrap 
from discord import TextStyle 


class TextModal(ui.Modal, title='Customize the reaction role message'):
    text = ui.TextInput(label='Enter message text here', style=TextStyle.long)

    def __init__(self, embed):
        self.embed = embed 

    async def on_submit(self, inter):
        self.embed.clear_fields()
        self.embed.set_field_at(0, name='Message Text', value=str(self.text))
        await inter.response.edit_message(embed=self.embed)


class RRView1(ui.View):
    def __init__(self, ctx, embed, options):
        self.ctx = ctx
        self.ready = False 
        self.embed = embed

        self.message = None 
        self.embedname = None 

        self.modal = None 

        super().__init__(timeout=None)

        for option in options:
            self.embedsel.add_option(label=option)
    
    @ui.button(label='Add message text', style=ButtonStyle.green)
    async def addmsg(self, inter, button):
        self.modal = TextModal(self.embed)
        await inter.response.send_modal(self.modal)
        await self.modal.wait()
        self.message = str(self.modal.text)
    
    @ui.select(placeholder='Choose an embed')
    async def embedsel(self, inter, select):
        self.embedname = select.values[0]
        self.embed.set_field_at(1, name='Embed', value=self.embedname)
        await inter.response.edit_message(embed=self.embed)

    @ui.button(label='Submit', style=ButtonStyle.green)
    async def submit(self, inter, button):
        if not (self.message or self.embed):
            await inter.response.send_message('Please enter either a message or an embed.', ephemeral=True)
            return 

        await inter.response.delete_message()
        
        self.ready = True 
        self.stop()

    @ui.button(label='Quit', style=ButtonStyle.red)
    async def quitbtn(self, inter, button):
        await inter.response.delete_message()
        self.stop()



class Joever(ValueError):
    ... 

async def parsemap(ctx, text):
    econv = commands.EmojiConverter()
    rconv = commands.RoleConverter()
    stuff = {}
    for line in text.splitlines():
        x = line.split()
        if len(x) != 2:
            raise Joever()
        try:
            emoji = await econv.convert(ctx, x[0])
            role = await rconv.convert(ctx, x[1])
        except (commands.CommandError, commands.BadArgument):
            raise Joever()
        stuff[str(emoji)] = role.id 

    if len(stuff) == 0:
        raise Joever()
    
    return stuff


class RRView2(ui.View):

    async def interaction_check(self, interaction):
        if interaction.user.id == self.ctx.author.id:
            return True 
        else:
            await interaction.response.defer()
            return False 
    
    def __init__(self, ctx, length):
        self.ez.add_option(label='No limit', value=-1)
        
        for i in range(1, length):
            self.ez.add_option(label=str(i), value=i)

        self.ctx = ctx 
        self.limit = None
        self.ready = False 
        super().__init__(timeout=None)


    @ui.select()
    async def ez(self, inter, select):
        self.limit = select.values[0]
        self.ready = True 
        await inter.response.delete_message()

    @ui.button(label='Submit', style=ButtonStyle.green)
    async def submit(self, inter, button):
        await inter.response.delete_message()
        self.stop()


class TimeModal(ui.Modal, title='Set minimum time since joining'):
    def __init__(self, embed):
        self.embed = embed 
        self.seconds = 0

    days = ui.TextInput(label='Days', default='0')
    hours = ui.TextInput(label='Hours', default='0')
    minutes = ui.TextInput(label='Minutes', default='0')

    async def on_submit(self, inter):
        try:
            days = int(str(self.days))
            hours = int(str(self.hours))
            minutes = int(str(self.minutes))
        except ValueError:
            return await inter.response.send_message('Please enter a valid time.', ephemeral=True)

        secs = days * 86400 + hours * 3600 + minutes * 60
        if secs <= 0:
            secs = 0
        self.secs = secs 
        if self.secs == 0:
            val = 'None'
        else:
            val = f'{self.secs} seconds\n\n**:warning: Needs deny message**'
        
        self.embed.set_field_at(1, name='Required Time', value=val)
        await inter.response.edit_message(embed=self.embed)

class RoleDenyModal(ui.Modal, title='When user doesn\'t have a role'):
    text = ui.TextInput(label='Enter message here', style=TextStyle.long)

    def __init__(self, embed):
        self.embed = embed
        self.denymsg = None

    async def on_submit(self, inter):
        gg = self.embed.fields[0].split('\n\n')[0]
        self.embed.set_field_at(0, name='Required Role', value=f'{gg}\n\n**:white_check_mark: Has deny message**')
        self.denymsg = str(self.text)
        await inter.response.edit_message(embed=self.embed)

class TimeDenyModal(ui.Modal, title='When user hasn\'t stayed long enough'):
    text = ui.TextInput(label='Enter message here', style=TextStyle.long, default="Use {time} for the remaining time thingy (DO NOT TYPE 'in' BEFORE IT)")


    def __init__(self, embed):
        self.embed = embed
        self.denymsg = None

    async def on_submit(self, inter):
        gg = self.embed.fields[1].split('\n\n')[0]
        self.embed.set_field_at(1, name='Required Time', value=f'{gg}\n\n**:white_check_mark: Has deny message**')
        self.denymsg = str(self.text)
        await inter.response.edit_message(embed=self.embed)
class RRView3(ui.View):
    def __init__(self, ctx, embed):
        self.ctx = ctx 
        self.embed = embed 
        self.role = None 
        self.modal = None 
        self.seconds = 0 
        self.role_denymsg = None 
        self.time_denymsg = None

    async def interaction_check(self, interaction):
        return interaction.user.id == self.ctx.author.id

    @ui.select(cls=ui.RoleSelect)
    async def roleselect(self, inter, select):
        self.role = select.values[0]
        self.role_denymsg = None
        self.embed.set_field_at(0, name='Required Role', value=f'{self.role.mention}\n\n**Requires deny message**')
        await inter.response.edit_message(embed=self.embed)
    
    @ui.button(label='Set time requirement', style=ButtonStyle.blurple)
    async def timebtn(self, inter, button):
        self.modal = TimeModal(self.embed)
        self.time_denymsg = None 
        await inter.response.send_modal(self.modal)
        await self.modal.wait()
        self.seconds = self.modal.seconds 
    
    @ui.button(label='Submit', style=ButtonStyle.green, row=2)
    async def submit(self, inter, button):
        if self.role is not None and self.role_denymsg is None:
            rdmodal = RoleDenyModal(self.embed)
            await inter.response.send_modal(rdmodal)
            await rdmodal.wait()
            self.role_denymsg = rdmodal.denymsg 
        elif self.seconds != 0 and self.time_denymsg is None:
            tdmodal = TimeDenyModal(self.embed)
            await inter.response.send_modal(tdmodal)
            await tdmodal.wait()
            self.time_denymsg = tdmodal.denymsg

        await inter.response.delete_message()
        
        self.ready = True 
        self.stop()

class RR(commands.Cog, name='Reaction Roles'):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # make the rr_selections table
        query = '''
                    CREATE TABLE IF NOT EXISTS rr_selections (
                        user_id BIGINT NOT NULL,
                        channel_id BIGINT NOT NULL,
                        message_id BIGINT NOT NULL,
                        role_id BIGINT NOT NULL,
                        PRIMARY KEY (user_id, channel_id, message_id, role_id)
                    )
                '''
        await self.bot.db.execute(query)

    
    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator or ctx.author.id == self.bot.STORCH_ID
    
    @commands.hybrid_command()
    async def addrr(self, ctx, *, channel: discord.TextChannel):
        embed = discord.Embed(
            title='Make the message for reactions to go under',
            color=0xcab7ff
        ).add_field(name='Message Text', value='None').add_field(name='Embed', value='None')
        query = 'SELECT name FROM embeds WHERE creator_id = ?'
        rows = await self.bot.db.fetch(query, ctx.author.id)
        options = [row[0] for row in rows]

        view1 = RRView1(ctx, embed, options)
        await ctx.send(embed=embed, view=view1)
        await view1.wait()

        if not view1.ready:
            return 
        
        embedout = None 
        if view1.embedname:
            query = 'SELECT embed FROM embeds WHERE name = ?'
            val = await self.bot.db.fetchval(query, view1.embedname)
            embedout = discord.Embed.from_dict(json.loads(val))
        
        await ctx.send(textwrap.dedent("""
        Enter each emoji and role pair for each reaction, on a different line. For example:

        :nerd: @Role1
        :clown: @Role2
        :skull: @Role3

        Please leave a space between the emoji and the role!
        """))

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel 
        
        joever = False 
        while not joever:
            msg = await self.bot.wait_for('message', check=check)
            try:
                stuff = await parsemap(ctx, msg.content)
                joever = True
            except Joever:
                await ctx.send('Something went wrong while parsing that! Please try again.')
        
        view2 = RRView2(ctx, len(stuff))
        await ctx.send('Choose a limit to the number of roles someone can get from this group:', view=view2)
        await view2.wait()

        if not view2.ready:
            return 
        
        embed = discord.Embed(
            title='Optional Settings',
            color=0xcab7ff
        ).add_field(name='Role Requirement', value='None').add_field(name='Time Requirement', value='None')
        view3 = RRView3(ctx, embed)
        await ctx.send(embed=embed, view=view3)
        await view3.wait()

        msgout = await channel.send(view1.message, embed=embedout)
        for emoji in stuff:
            await msgout.add_reaction(emoji)

        query = 'INSERT INTO rrs (channel_id, message_id, map, max_sel, req_role_id, no_role_msg, req_time, no_time_msg) VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
        await self.bot.db.execute(query, channel.id, msgout.id, json.dumps(stuff), view2.limit, view3.role.id if view3.role else None, view3.role_denymsg, view3.seconds, view3.time_denymsg)
        await ctx.send('Successfully added reaction role :white_check_mark:')

    @commands.hybrid_command()
    async def removerr(self, ctx, channel: discord.TextChannel, message_id: int):
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.send('Message not found.')

        await message.delete()
        query = 'DELETE FROM rrs WHERE channel_id = ? AND message_id = ?'
        await self.bot.db.execute(query, channel.id, message_id)
        await ctx.send('Successfully removed reaction role :white_check_mark:')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        query = 'SELECT map, max_sel, req_role_id, no_role_msg, req_time, no_time_msg FROM rrs WHERE channel_id = ? AND message_id = ?'
        row = await self.bot.db.fetchrow(query, payload.channel_id, payload.message_id)
        if row is None:
            return 

        if row['req_role_id'] is not None:
            if row['req_role_id'] not in [role.id for role in payload.member.roles]:
                if row['no_role_msg'] is not None:
                    await payload.member.send(row['no_role_msg'])
                return await payload.member.remove_reaction(payload.emoji, payload.member.guild.get_channel(payload.channel_id).get_partial_message(payload.message_id))

        if row['req_time'] is not None:
            if payload.member.joined_at is None:
                return await payload.member.remove_reaction(payload.emoji, payload.member.guild.get_channel(payload.channel_id).get_partial_message(payload.message_id))
            if (datetime.datetime.utcnow() - payload.member.joined_at).total_seconds() < row['req_time']:
                if row['no_time_msg'] is not None:
                    await payload.member.send(row['no_time_msg'].replace('{time}', discord.utils.format_dt(payload.member.joined_at + datetime.timedelta(seconds=row['req_time']), 'R')))
                return await payload.member.remove_reaction(payload.emoji, payload.member.guild.get_channel(payload.channel_id).get_partial_message(payload.message_id))

        if row['max_sel'] != -1:
            query = 'SELECT COUNT(*) FROM rr_selections WHERE user_id = ? AND channel_id = ? AND message_id = ?'
            count = await self.bot.db.fetchval(query, payload.user_id, payload.channel_id, payload.message_id)
            if count >= row['max_sel']:
                return await payload.member.remove_reaction(payload.emoji, payload.member.guild.get_channel(payload.channel_id).get_partial_message(payload.message_id))

        query = 'SELECT role_id FROM rr_selections WHERE user_id = ? AND channel_id = ? AND message_id = ?'
        rows = await self.bot.db.fetch(query, payload.user_id, payload.channel_id, payload.message_id)
        if payload.emoji.name in [str(row['role_id']) for row in rows]:
            return await payload.member.remove_reaction(payload.emoji, payload.member.guild.get_channel(payload.channel_id).get_partial_message(payload.message_id))

        map = json.loads(row['map'])
        if payload.emoji.name not in map:
            return await payload.member.remove_reaction(payload.emoji, payload.member.guild.get_channel(payload.channel_id).get_partial_message(payload.message_id))
        
        role = payload.member.guild.get_role(map[payload.emoji.name])
        await payload.member.add_roles(role)
        query = 'INSERT INTO rr_selections (user_id, channel_id, message_id, role_id) VALUES (?, ?, ?, ?)'
        await self.bot.db.execute(query, payload.user_id, payload.channel_id, payload.message_id, role.id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        query = 'SELECT map FROM rrs WHERE channel_id = ? AND message_id = ?'
        row = await self.bot.db.fetchrow(query, payload.channel_id, payload.message_id)
        if row is None:
            return 

        map = json.loads(row['map'])
        if payload.emoji.name not in map:
            return 

        role = payload.member.guild.get_role(map[payload.emoji.name])
        await payload.member.remove_roles(role)
        query = 'DELETE FROM rr_selections WHERE user_id = ? AND channel_id = ? AND message_id = ? AND role_id = ?'
        await self.bot.db.execute(query, payload.user_id, payload.channel_id, payload.message_id, role.id)


async def setup(bot):
    await bot.add_cog(RR(bot))
