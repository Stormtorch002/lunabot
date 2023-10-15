from discord.ext import commands 
from utils.views import RoboPages, AutoSource
from discord import ui
from discord.interactions import Interaction
from embed_editor.editor import EmbedEditor
import discord 
import json 
import asyncio 
import re 
from lunascript import LunaScript


class RoleView(ui.View):

    def __init__(self):
        super().__init__()
        self.ready = False 
        self.roles = []
        self.inter = None 

    @ui.select(cls=ui.RoleSelect, min_values=0, max_values=None)
    async def rolesel(self, inter, sel):
        self.inter = inter 
        self.roles = sel.values 
        self.ready = True
        self.stop()

    @ui.button(label='Clear all roles')
    async def clearbtn(self, inter, btn):
        self.inter = inter 
        self.roles = []
        self.ready = True
        self.stop()


class AutoResponder:

    def __init__(self, phrase, detection, guilds, wlusers, blusers, wlroles, blroles, wlchannels, blchannels, text, embed, autoemojis, give_roles=None, remove_roles=None, delete_trigger=None, delete_response_after=None):
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
        self.embed = embed 
        self.autoemojis = json.loads(autoemojis) if autoemojis else []
        self.give_roles = json.loads(give_roles) if give_roles else []
        self.remove_roles = json.loads(remove_roles) if remove_roles else []
        self.delete_trigger = delete_trigger if delete_trigger else False
        self.delete_response_after = delete_response_after
    
    def __eq__(self, other):
        return self.phrase == other.phrase
    

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
                        AutoResponder(*[row[i] for i in range(1, 17)])
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
            if ar.wlchannels and msg.channel.id not in ar.wlchannels:
                continue 
            if ar.blchannels and msg.channel.id in ar.blchannels:
                continue 
            
            content = msg.content.lower()
            args = None 

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
                match = re.search(ar.phrase, msg.content, re.IGNORECASE)
                if not match: 
                    continue 
                args = match.groups()

            if ar.autoemojis:
                for emoji in ar.autoemojis:
                    await msg.add_reaction(emoji)
            else:
                if ar.embed:
                    embed = self.bot.embeds.get(ar.embed)
                else:
                    embed = None

                # await msg.channel.send(ar.text, embed=embed, delete_after=ar.delete_response_after)
                ls = LunaScript(await self.bot.get_context(msg), ar.text, embed, args=args)
                await ls.send()
            
            for roleid in ar.give_roles:
                role = msg.guild.get_role(roleid) 
                if role not in msg.author.roles:
                    await msg.author.add_roles(role)
            for roleid in ar.remove_roles:
                role = msg.guild.get_role(roleid) 
                if role in msg.author.roles:
                    await msg.author.remove_roles(role)

            if ar.delete_trigger:
                await msg.delete()


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
            await inter.response.edit_message(view=None)
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
            
            await inter.response.edit_message(view=None)
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
        

        # make a view for user to select either message responder or autoreaction
        class View(ui.View):
                
            def __init__(self):
                super().__init__()
                self.ready = False 
                self.choice = None
                self.inter = None  

            async def interaction_check(self, interaction):
                return interaction.user == ctx.author 

            @ui.select(options=[discord.SelectOption(label=gg) for gg in ['message', 'autoreaction']])        
            async def allowtype(self, inter, sel):
                self.choice = sel.values[0]
                self.inter = inter 
                self.ready = True 
                self.stop()

        view2 = View()
        msg = await ctx.send('What type of autoresponder would you like to make?', view=view2)
        await view2.wait()
        if not view2.ready:
            await msg.delete()
            return
        
        
        if view2.choice == 'message':
            
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel 
            
            await view2.inter.response.send_message("Please type the text component of the autoresponse. Type `skip` to skip this step.")
            resp = await self.bot.wait_for('message', check=check)
            if resp.content.lower() == 'skip':
                text = None 
            else:
                text = resp.content

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            if text is None:
                skippable = False
                temp = await ctx.send("Please enter the name of an embed.")
            else:
                skippable = True
                temp = await ctx.send("Please enter the name of an embed, or type `skip` to skip.")

            try:
                msg2 = await self.bot.wait_for('message', check=check, timeout=180)
            except asyncio.TimeoutError:
                await temp.delete()
                return 
            
            if not skippable:
                query = 'SELECT name FROM embeds WHERE name = ?'
                val = await self.bot.db.fetchval(query, msg2.content.lower())
                if val is None:
                    return await ctx.send('No embed with that name found.')
                embed_name = val 
            else:
                if msg2.content.lower() == 'skip':
                    embed_name = None 
                else:
                    query = 'SELECT name FROM embeds WHERE name = ?'
                    val = await self.bot.db.fetchval(query, msg2.content.lower())
                    if val is None:
                        return await ctx.send('No embed with that name found.')
                    embed_name = val 

            self.ars.append(
                AutoResponder(phrase.lower(), choice, json.dumps(guild_ids), '[]', '[]', '[]', '[]', '[]', '[]', text, embed_name, [])
            )
            async with self.bot.pool.acquire() as conn:
                query = '''INSERT INTO ars (phrase, detection, guilds, message, embed)
                            VALUES (?, ?, ?, ?, ?)'''
                await conn.execute(query, (phrase.lower(), choice, json.dumps(guild_ids), text, embed_name))
                await conn.commit()
        else:
            emojis = await self.getemojis(ctx, view2.inter)
            if not emojis:
                return await ctx.send('Please provide at least one valid emoji, autoresponder cancelled.')

            query = 'INSERT INTO ars (phrase, detection, guilds, emojis) VALUES (?, ?, ?, ?)'

            self.ars.append(
                AutoResponder(phrase.lower(), choice, json.dumps(guild_ids), '[]', '[]', '[]', '[]', '[]', '[]', None, None, emojis)
            )
            await self.bot.db.execute(query, phrase.lower(), choice, json.dumps(guild_ids), emojis)
            
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
    async def editar(self, ctx, *, phrase):
        # create a select menu with the following choices: allow, deny, add autoreaction, remove autoreaction 
        phrase = phrase.lower()
        for ar in self.ars:
            if ar.phrase == phrase:
                break
        else:
            return await ctx.send('No autoresponder with that phrase.')
        
        class View(ui.View):
                
            def __init__(self):
                super().__init__()
                self.ready = False 
                self.choice = None
                self.inter = None  

            async def interaction_check(self, interaction):
                return interaction.user == ctx.author 

            @ui.select(options=[discord.SelectOption(label=gg) for gg in ['whitelist', 'blacklist', 'roles given', 'roles removed', 'trigger deletion', 'response deletion']])        
            async def allowtype(self, inter, sel):
                self.choice = sel.values[0]
                self.inter = inter 
                self.ready = True 
                self.stop()

            
        view = View()
        msg = await ctx.send('What would you like to edit?', view=view)
        await view.wait()
        if not view.ready:
            await msg.delete()
            return

        if view.choice == 'whitelist':
            await self.allowar(ctx, view.inter, phrase=phrase)
        elif view.choice == 'blacklist':
            await self.denyar(ctx, view.inter, phrase=phrase)
        elif view.choice == 'roles given':
            view2 = RoleView()
            await view.inter.response.edit_message(content='Please select all the roles to give (overrides old settings).', view=view2)
            await view2.wait()
            if not view2.ready:
                return 
            roleids = [r.id for r in view2.roles]
            self.ars.remove(ar)
            ar.give_roles = roleids
            self.ars.append(ar)
            query = 'UPDATE ars SET give_roles = ? WHERE phrase = ?'
            await self.bot.db.execute(query, json.dumps(roleids), phrase)
            await view2.inter.response.edit_message(content='Edited your autoresponder!', view=None)
        elif view.choice == 'roles removed':
            view2 = RoleView()
            await view.inter.response.edit_message(content='Please select all the roles to remove (overrides old settings).', view=view2)
            await view2.wait()
            if not view2.ready:
                return 
            roleids = [r.id for r in view2.roles]
            self.ars.remove(ar)
            ar.remove_roles = roleids
            self.ars.append(ar)
            query = 'UPDATE ars SET remove_roles = ? WHERE phrase = ?'
            await self.bot.db.execute(query, json.dumps(roleids), phrase)
            await view2.inter.response.edit_message(content='Edited your autoresponder!', view=None)
        elif view.choice == 'trigger deletion':

            class TriggerView(ui.View):

                def __init__(self):
                    super().__init__()
                    self.inter = None 
                    self.ready = False 
                    self.choice = None 

                @ui.button(label='Delete trigger')
                async def b1(self, inter, button):
                    self.inter = inter 
                    self.ready = True 
                    self.choice = True
                    self.stop()

                @ui.button(label='Don\'t delete trigger', row=1)
                async def b2(self, inter, button):
                    self.inter = inter 
                    self.ready = True 
                    self.choice = False
                    self.stop()

            view2 = TriggerView()
            await view.inter.response.send_message('Choose an option', view=view2)
            await view2.wait()
            if not view2.ready:
                return 
            self.ars.remove(ar)
            ar.delete_trigger = view2.choice 
            self.ars.append(ar)
            query = 'UPDATE ars SET delete_trigger = ? WHERE phrase = ?'
            await self.bot.db.execute(query, int(view2.choice), phrase)
            await view2.inter.response.edit_message(content='Edited your autoresponder!', view=None)
        elif view.choice == 'response deletion':
            def check(m):
                return m.channel == ctx.channel and m.author == ctx.author 
            first = True 
            while True:
                if first:
                    temp = await view.inter.response.send_message('Enter the number of seconds you want the response to last before being deleted. 0 means it won\'t be deleted.')
                    first = False 
                else:
                    temp = await ctx.send('Please enter a valid number:')
                try:
                    msg = await self.bot.wait_for('message', check=check, timeout=180)
                except asyncio.TimeoutError:
                    await temp.delete()
                    return
                try:
                    delay = int(msg.content)
                    break
                except ValueError:
                    continue

            if delay <= 0:
                delay = None
            self.ars.remove(ar)
            ar.delete_response_after = delay 
            self.ars.append(ar)
            query = 'UPDATE ars SET delete_response_after = ? WHERE phrase = ?' 
            await self.bot.db.execute(query, delay, phrase)
            await ctx.send('Edited your autoresponder!')


            
    async def getemojis(self, ctx, inter):
        temp = await inter.response.send_message('Please send one or more emojis, separated by spaces.')

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            resp = await self.bot.wait_for('message', check=check, timeout=300)
        except asyncio.TimeoutError:
            await temp.delete()
            return await ctx.send('You took too long to respond.')
        
        args = resp.content.split()
        emojis = []
        conv = commands.EmojiConverter()
        errs = []
        for arg in args:
            try:
                emoji = await conv.convert(ctx, arg)
            except commands.EmojiNotFound:
                errs.append(f'Emoji {arg} not found.')
                continue 
            emojis.append(emoji)
        if errs:
            await ctx.send('\n'.join(errs))
        
        emojis_json = json.dumps([str(emoji) for emoji in emojis])
        return emojis_json 

        
    async def allowar(self, ctx, inter, phrase):

        class View(ui.View):

            def __init__(self):
                super().__init__()
                self.ready = False 
                self.choice = None
                self.inter = None  

            async def interaction_check(self, interaction):
                return interaction.user == ctx.author 

            @ui.select(options=[discord.SelectOption(label=gg) for gg in ['channel', 'role', 'user']])        
            async def allowtype(self, inter, sel):
                self.choice = sel.values[0]
                self.inter = inter 
                self.ready = True 
                self.stop() 
        
        view = View()
        msg = await inter.response.send_message('What would you like to allow?', view=view)
        await view.wait()
        if not view.ready:
            await msg.delete()
            return 
        
        if view.choice == 'channel':
            c = ui.ChannelSelect
        elif view.choice == 'role':
            c = ui.RoleSelect
        else:
            c = ui.UserSelect 
        
        class View2(ui.View):

            def __init__(self):
                super().__init__()
                self.ready = False 
                self.inter = None 
                self.choices = None 

            async def interaction_check(self, interaction):
                return interaction.user == ctx.author 

            @ui.select(cls=c, min_values=0, max_values=25, channel_types=[discord.ChannelType.text])
            async def objselect(self, inter, sel):
                self.ready = True 
                self.inter = inter 
                self.choices = sel.values 
                self.stop() 

            @ui.button(label='Clear all roles')
            async def clearbtn(self, inter, btn):
                self.inter = inter 
                self.choices = []
                self.ready = True
                self.stop()

        view2 = View2()
        await view.inter.response.send_message(f'Please choose the {view.choice}s to allow:', view=view2) 
        await view2.wait()
        if not view2.ready:
            return 
        
        for ar in self.ars:
            if ar.phrase == phrase:
                self.ars.remove(ar)
                break 
        temp = ar     
        ids = [o.id for o in view2.choices]
        if c is ui.ChannelSelect:
            col = 'wlchannels'
            temp.wlchannels = ids 
        elif c is ui.RoleSelect:
            col = 'wlroles' 
            temp.wlroles = ids 
        else:
            col = 'wlusers'
            temp.wlusers = ids
        self.ars.append(temp) 
        col2 = col.replace('w', 'b')

        query = f'UPDATE ars SET {col} = ?, {col2} = ? WHERE phrase = ?'
        await self.bot.db.execute(query, json.dumps(ids), '[]', phrase)
         
        await view2.inter.response.edit_message(view=None, content='Edited your autoresponder!')

    async def denyar(self, ctx, inter, phrase):

        class View(ui.View):

            def __init__(self):
                super().__init__()
                self.ready = False 
                self.choice = None
                self.inter = None  

            async def interaction_check(self, interaction):
                if interaction.user.id == self.ctx.author.id:
                    return True 
                else:
                    await interaction.response.defer()
                    return False 

            @ui.select(options=[discord.SelectOption(label=gg) for gg in ['channel', 'role', 'user']])        
            async def allowtype(self, inter, sel):
                self.choice = sel.values[0]
                self.inter = inter 
                self.ready = True 
                self.stop() 
        
        view = View()
        msg = await inter.response.send_message('What would you like to allow?', view=view)
        await view.wait()
        if not view.ready:
            await msg.delete()
            return 
        
        if view.choice == 'channel':
            c = ui.ChannelSelect
        elif view.choice == 'role':
            c = ui.RoleSelect
        else:
            c = ui.UserSelect 
        
        class View2(ui.View):

            def __init__(self):
                super().__init__()
                self.ready = False 
                self.inter = None 
                self.choices = None 

            async def interaction_check(self, interaction):
                return interaction.user == ctx.author 

            @ui.select(cls=c, max_values=25, channel_types=[discord.ChannelType.text])
            async def objselect(self, inter, sel):
                self.ready = True 
                self.inter = inter 
                self.choices = sel.values 
                self.stop() 

        view2 = View2()
        await view.inter.response.send_message(f'Please choose the {view.choice}s to deny:', view=view2)            
        await view2.wait()
        if not view2.ready:
            return 
        
        for ar in self.ars:
            if ar.phrase == phrase:
                self.ars.remove(ar)
                break 
        temp = ar     
        ids = [o.id for o in view2.choices]
        if c is ui.ChannelSelect:
            col = 'blchannels'
            temp.blchannels = ids 
        elif c is ui.RoleSelect:
            col = 'blroles' 
            temp.blroles = ids 
        else:
            col = 'blusers'
            temp.blusers = ids
        self.ars.append(temp) 
        col2 = col.replace('b', 'w')

        query = f'UPDATE ars SET {col} = ?, {col2} = ? WHERE phrase = ?'
        await self.bot.db.execute(query, json.dumps(ids), '[]', phrase)
         
        await view2.inter.response.edit_message(view=None, content='Edited your autoresponder!')
     
    # @commands.command()
    # async def addarwl(self, ctx, objects: Greedy[Union[Member, Role, TextChannel]], *, phrase):
    #     if len(objects) == 0:
    #         return await ctx.send("Please provide at least one member, role, or channel before the phrase")
        
    #     async with self.bot.pool.acquire() as conn:
    #         for ar in self.ars:
    #             if ar.phrase == phrase.lower():
    #                 embed = discord.Embed(title='Added the following to the whitelist', color=0xcab7ff)
    #                 ked = []
    #                 for obj in objects:
    #                     if isinstance(obj, Member):
    #                         if obj.id in ar.wlusers:
    #                             continue 
    #                         ar.wlusers.append(obj.id)
    #                         query = 'UPDATE ars SET wlusers = ? WHERE phrase = ?'
    #                         await conn.execute(query, (json.dumps(ar.wlusers), phrase))
    #                     elif isinstance(obj, Role):
    #                         if obj.id in ar.wlroles:
    #                             continue 
    #                         ar.wlroles.append(obj.id)
    #                         query = 'UPDATE ars SET wlroles = ? WHERE phrase = ?'
    #                         await conn.execute(query, (json.dumps(ar.wlroles), phrase))
    #                     else:
    #                         if obj.id in ar.wlchannels:
    #                             continue 
    #                         ar.wlchannels.append(obj.id)
    #                         query = 'UPDATE ars SET wlchannels = ? WHERE phrase = ?'
    #                         await conn.execute(query, (json.dumps(ar.wlchannels), phrase))
    #                     ked.append(obj.mention)
    #                 embed.description = '\n'.join(ked)
    #                 await ctx.send(embed=embed)

    #                 # remove blacklist
    #                 return 
    #     await ctx.send('No autoresponder with that name.')
    
    
    @commands.command()
    async def listar(self, ctx):
        ars = [(ar.phrase, ar.detection) for ar in self.ars if ar.g]
        # split into chunks of 10
        ar_chunks = [ars[i:i+10] for i in range(0, len(ars), 10)]
        embeds = []
        for i, ars in enumerate(ar_chunks):
            embed = discord.Embed(title=f'Autoresponders (page {i+1}/{len(ar_chunks)})', color=0xcab7ff)
            embed.description = '\n'.join([f'{phrase} ({detection})' for phrase, detection in ars])
            embeds.append(embed)
            
        view = RoboPages(AutoSource(embeds), ctx=ctx)
        await view.start()




async def setup(bot):
    await bot.add_cog(AutoResponderCog(bot))

