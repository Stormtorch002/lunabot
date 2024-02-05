from discord.ext import commands 
from discord import ui
import discord 
import json 
import asyncio 
import re 
from lunascript import LunaScript


class AllowDenyView(ui.View):
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

    def __init__(self, phrase, data):
        self.phrase = phrase 
        self.data = data

        self.detection = self.data["detection"]
        self.guilds = self.data.get("guilds", '[]')

        # whitelists/blacklists
        self.wlusers = self.data.get("wlusers", [])
        self.blusers = self.data.get("blusers", [])
        self.wlroles = self.data.get("wlroles", [])
        self.blroles = self.data.get("blroles", [])
        self.wlchannels = self.data.get("wlchannels", [])
        self.blchannels = self.data.get("blchannels", [])

        # responding
        self.text = self.data.get("text", None)
        self.embed = self.data.get("embed", None)
        self.autoemojis = self.data.get("autoemojis", [])
        self.give_roles = self.data.get("give_roles", [])
        self.remove_roles = self.data.get("remove_roles", [])
        self.delete_trigger = self.data.get("delete_trigger", False)
        self.delete_response_after = self.data.get("delete_response_after", None)

        # cooldowns 
        self.guild_cooldown = self.data.get("guild_cooldown", None)
        self.channel_cooldown = self.data.get("channel_cooldown", None) 
        self.user_cooldown = self.data.get("user_cooldown", None)
        
        if self.guild_cooldown is not None:
            self.guild_cooldown = commands.CooldownMapping.from_cooldown(1, self.guild_cooldown, commands.BucketType.guild)
            # self.guild_cooldown = commands.Cooldown(1, self.guild_cooldown)
        if self.channel_cooldown is not None:
            self.channel_cooldown = commands.CooldownMapping.from_cooldown(1, self.channel_cooldown, commands.BucketType.channel)
            # self.channel_cooldown = commands.Cooldown(1, self.channel_cooldown)
        if self.user_cooldown is not None:
            self.user_cooldown = commands.CooldownMapping.from_cooldown(1, self.user_cooldown, commands.BucketType.user)
            # self.user_cooldown = commands.Cooldown(1, self.user_cooldown)
    
    def __eq__(self, other):
        return self.phrase == other.phrase
    

class AutoResponderCog(commands.Cog, name='Autoresponders', description="Autoresponder stuff (admin only)"):
    def __init__(self, bot):
        self.bot = bot 
        self.ars = []
    
    async def cog_load(self):
        query = 'SELECT * FROM ars'
        rows = await self.bot.db.fetch(query)
        for row in rows:
            data = json.loads(row["data"])
            self.ars.append(
                AutoResponder(row['phrase'], data)
            )

    async def cog_unload(self):
        self.ars = []

    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator or await self.bot.is_owner(ctx.author)
    
    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot: 
            return 
        
        for ar in self.ars:
            if msg.guild.id not in ar.guilds:
                continue 
            if ar.wlusers and msg.author.id not in ar.wlusers:
                continue 
            if ar.blusers and msg.author.id in ar.blusers:
                continue 
            roleids = [r.id for r in msg.author.roles]
            if ar.wlroles and all(role not in roleids for role in ar.wlroles):
                continue 
            if ar.blroles and any(role in roleids for role in ar.blroles):
                continue 
            if ar.wlchannels and msg.channel.id not in ar.wlchannels:
                continue 
            if ar.blchannels and msg.channel.id in ar.blchannels:
                continue 
            
            cds = [ar.guild_cooldown, ar.channel_cooldown, ar.user_cooldown]
            on_cd = False
            for cd in cds:
                # print(cd, type(cd))
                if cd is None:
                    continue

                bucket = cd.get_bucket(msg)
                retry_after = bucket.update_rate_limit()
                if retry_after:
                    #print(f'guild cooldown for {ar.phrase} in {msg.guild.name}')
                    on_cd = True
                    continue 

                if on_cd:
                    break
            
            if on_cd:
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
                    if embed is None:
                        embed = discord.Embed.from_dict(json.loads(ar.embed))
                else:
                    embed = None

                # await msg.channel.send(ar.text, embed=embed, delete_after=ar.delete_response_after)
                # print(ar.text, embed)
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

            query = '''INSERT INTO ars (phrase, data) VALUES (?, ?)'''
            data = {
                "detection": choice,
                "guilds": guild_ids,
                "text": text,
                "embed": embed_name,
            }
            await self.bot.db.execute(query, phrase.lower(), json.dumps(data))
            self.ars.append(AutoResponder(phrase.lower(), data))
        else:
            emojis = await self.getemojis(ctx, view2.inter)
            if not emojis:
                return await ctx.send('Please provide at least one valid emoji, autoresponder cancelled.')

            query = 'INSERT INTO ars (phrase, data) VALUES (?, ?)'  
            data = {
                "detection": choice,
                "guilds": guild_ids,
                "autoemojis": emojis,
            }
            await self.bot.db.execute(query, phrase.lower(), json.dumps(data))
            self.ars.append(AutoResponder(phrase.lower(), data))
            
        await ctx.send('Successfully made autoresponder!')

    @commands.command()
    async def removear(self, ctx, *, phrase):
        """Removes an autoresponder."""
        for ar in self.ars:
            if ar.phrase == phrase.lower():
                self.ars.remove(ar)
                query = '''DELETE FROM ars WHERE phrase = ?'''
                await self.bot.db.execute(query, phrase.lower())
                return await ctx.send('Successfully removed autoresponder.')

        await ctx.send('No autoresponder with that name.')

    async def edit_cd(self, inter, ar):
        class View(ui.View):

            def __init__(self):
                super().__init__()
                self.ready = False 
                self.choice = None
                self.inter = None  

            async def interaction_check(self, interaction):
                return interaction.user == inter.user 

            @ui.select(options=[discord.SelectOption(label=gg) for gg in ['guild', 'channel', 'user']])        
            async def allowtype(self, inter, sel):
                self.choice = sel.values[0]
                self.inter = inter 
                self.ready = True 
                self.stop() 
        
        view = View()
        msg = await inter.response.send_message('What cooldown would you like to edit?', view=view)
        await view.wait()
        if not view.ready:
            await msg.delete()
            return 
        
        await view.inter.response.send_message('Please enter the new cooldown in seconds. 0 means no cooldown.')

        def check(m):
            return m.author == inter.user and m.channel == inter.channel
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=180)
        except asyncio.TimeoutError:
            return await inter.response.edit_message(content='You took too long to respond.', view=None)
        
        if not msg.content.isdigit():
            return await inter.response.edit_message(content='Please enter a valid number.', view=None)

        cd = int(msg.content)

        if cd == 0:
            cd = None

        if view.choice == 'guild':
            if cd is None:
                ar.guild_cooldown = None 
                del ar.data['guild_cooldown']
            else: 
                ar.guild_cooldown = commands.CooldownMapping.from_cooldown(1, cd, commands.BucketType.guild)
                ar.data['guild_cooldown'] = cd
        elif view.choice == 'channel':
            if cd is None:
                ar.channel_cooldown = None 
                del ar.data['channel_cooldown']
            else:
                ar.channel_cooldown = commands.CooldownMapping.from_cooldown(1, cd, commands.BucketType.channel)
                ar.data['channel_cooldown'] = cd
        else:
            if cd is None:
                ar.user_cooldown = None 
                del ar.data['user_cooldown']
            else:
                ar.user_cooldown = commands.CooldownMapping.from_cooldown(1, cd, commands.BucketType.user)
                ar.data['user_cooldown'] = cd
        
        query = 'UPDATE ars SET data = ? WHERE phrase = ?'
        await self.bot.db.execute(query, json.dumps(ar.data), ar.phrase)
        await msg.reply('Edited cooldown!', view=None)

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

            @ui.select(options=[discord.SelectOption(label=gg) for gg in ['whitelist', 'blacklist', 'cooldown', 'roles given', 'roles removed', 'trigger deletion', 'response deletion']])        
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
            await self.allowar(view.inter, ar)
        elif view.choice == 'blacklist':
            await self.denyar(view.inter, ar)
        elif view.choice == 'cooldown':
            await self.edit_cd(view.inter, ar)
        elif view.choice == 'roles given':
            view2 = RoleView()
            await view.inter.response.edit_message(content='Please select all the roles to give (overrides old settings).', view=view2)
            await view2.wait()
            if not view2.ready:
                return 
            roleids = [r.id for r in view2.roles]
            ar.data['give_roles'] = roleids
            ar.give_roles = roleids
            query = 'UPDATE ars SET data = ? WHERE phrase = ?'
            await self.bot.db.execute(query, json.dumps(ar.data), phrase)
            await view2.inter.response.edit_message(content='Edited your autoresponder!', view=None)
        elif view.choice == 'roles removed':
            view2 = RoleView()
            await view.inter.response.edit_message(content='Please select all the roles to remove (overrides old settings).', view=view2)
            await view2.wait()
            if not view2.ready:
                return 
            roleids = [r.id for r in view2.roles]
            ar.data['remove_roles'] = roleids
            ar.remove_roles = roleids
            query = 'UPDATE ars SET data = ? WHERE phrase = ?'
            await self.bot.db.execute(query, json.dumps(ar.data), phrase)
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
            ar.data['delete_trigger'] = view2.choice
            ar.delete_trigger = view2.choice
            query = 'UPDATE ars SET data = ? WHERE phrase = ?'
            await self.bot.db.execute(query, json.dumps(ar.data), phrase)
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
            ar.delete_response_after = delay
            ar.data['delete_response_after'] = delay
            query = 'UPDATE ars SET data = ? WHERE phrase = ?'
            await self.bot.db.execute(query, json.dumps(ar.data), phrase)
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
        
    async def allowar(self, inter, ar):
        view = AllowDenyView()
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
                return interaction.user == inter.user

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

        ids = [o.id for o in view2.choices]
        if c is ui.ChannelSelect:
            ar.data['wlchannels'] = ids
            ar.wlchannels = ids
        elif c is ui.RoleSelect:
            ar.data['wlroles'] = ids
            ar.wlroles = ids
        else:
            ar.data['wlusers'] = ids
            ar.wlusers = ids

        query = 'UPDATE ars SET data = ? WHERE phrase = ?'
        await self.bot.db.execute(query, json.dumps(ar.data), ar.phrase)
        await view2.inter.response.edit_message(view=None, content='Edited your autoresponder!')

    async def denyar(self, inter, ar):
        view = AllowDenyView()
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
                return interaction.user == inter.user 

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

        ids = [o.id for o in view2.choices]
        if c is ui.ChannelSelect:
            ar.data['blchannels'] = ids
            ar.blchannels = ids
        elif c is ui.RoleSelect:
            ar.data['blroles'] = ids
            ar.blroles = ids
        else:
            ar.data['blusers'] = ids
            ar.blusers = ids

        query = 'UPDATE ars SET data = ? WHERE phrase = ?'
        await self.bot.db.execute(query, json.dumps(ar.data), ar.phrase)
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
    async def listar(self, ctx, page: int = 1):
        ars = [(ar.phrase, ar.detection) for ar in self.ars if ctx.guild.id in ar.guilds]
        # split into chunks of 10
        ar_chunks = [ars[i:i+10] for i in range(0, len(ars), 10)]
        embeds = []
        for i, ars in enumerate(ar_chunks):
            embed = discord.Embed(title=f'Autoresponders (page {i+1}/{len(ar_chunks)})', color=0xcab7ff)
            embed.description = '\n'.join([f'{phrase} ({detection})' for phrase, detection in ars])
            embeds.append(embed)
            
        try:
            await ctx.send(embed=embeds[page-1])
        except IndexError:
            await ctx.send('No page with that number.')




async def setup(bot):
    await bot.add_cog(AutoResponderCog(bot))

