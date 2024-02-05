from discord.ext import commands 
import discord 


class StickyMessages(commands.Cog):

    def __init__(self, bot):
        self.bot = bot 
        self.data = {}

    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator or ctx.author.id == self.bot.STORCH_ID 

    async def cog_load(self):
        query = 'select * from stickymessages'
        rows = await self.bot.db.fetch(query)
        for row in rows:
            self.data[row['channel_id']] = [row['text'], row['embed'], row['last_msg_id']]
    
    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return 

        if msg.channel.id in self.data:
            text, embed, last_msg_id = self.data[msg.channel.id]

            embed = self.bot.embeds.get(embed)
            if embed is None:
                embed = discord.Embed(title='Embed not found')
            if text is None:
                text = ''

            new_msg = await msg.channel.send(text, embed=embed)

            self.data[msg.channel.id][2] = new_msg.id
            query = 'update stickymessages set last_msg_id = ? where channel_id = ?'
            await self.bot.db.execute(query, new_msg.id, msg.channel.id)

            if last_msg_id is None:
                return 
            try:
                old_msg = await msg.channel.fetch_message(last_msg_id)
                await old_msg.delete()
            except discord.NotFound:
                pass

    @commands.command()
    async def addsm(self, ctx, *, channel: discord.TextChannel):
        # ask for the text and then embed name 

        await ctx.send('What would you like the text to be? Type `skip` to skip.')
        msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        text = msg.content

        if text.lower() == 'skip':
            text = None
            ending = ''
        else:
            ending = ' Type `skip` to skip.'

        await ctx.send(f'What would you like the embed to be?{ending}')
        msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel)

        if text is not None and msg.content.lower() == 'skip':
            embed = None 
        else:
            if msg.content.lower() not in self.bot.embeds:
                await ctx.send('That embed does not exist.')
                return
            embed = msg.content.lower()

        query = 'insert into stickymessages values (?, ?, ?, ?)'
        await self.bot.db.execute(query, channel.id, text, embed, None)
        self.data[channel.id] = [text, embed, None]
    
    @commands.command()
    async def removesm(self, ctx, *, channel: discord.TextChannel):
        if channel.id not in self.data:
            await ctx.send('That channel does not have a sticky message.')
            return

        query = 'delete from stickymessages where channel_id = ?'
        await self.bot.db.execute(query, channel.id)
        del self.data[channel.id]
        await ctx.send('Successfully removed the sticky message.')

    @commands.command()
    async def listsm(self, ctx):
        channels = []
        for channel_id in self.data:
            channel = self.bot.get_channel(channel_id)
            if channel.guild == ctx.guild and channel_id in self.data:
                channels.append(ctx.guild.get_channel(channel_id).mention)
        
        channels = '\n'.join(channels)
        embed = discord.Embed(title='Sticky Messages', description=channels, color=0xcab7ff)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(StickyMessages(bot))
