from discord.ext import commands 
from embeds import fill_embed
import discord 


ART_HOF_CHANNEL_ID = 1191559069627060284
ART_CHANNEL_IDS = [
    1191555710291554395,
    1191555765241131059,
    1191558039636025485,
    1191979119173447841
]
THRESHOLD = 3


class ArtHof(commands.Cog):

    def __init__(self, bot):
        self.bot = bot 

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.channel.id not in ART_CHANNEL_IDS:
            return
        if msg.author.bot:
            return
        await msg.add_reaction(self.bot.vars.get('artHofEmote'))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.channel_id not in ART_CHANNEL_IDS:
            return
        
        if str(payload.emoji) != self.bot.vars.get('artHofEmote'):
            return

        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if message.author.id == payload.user_id:
            return
        reaction = discord.utils.get(message.reactions, emoji=payload.emoji)

        query = 'SELECT * FROM arthof WHERE original_id = ?' 
        row = await self.bot.db.fetchrow(query, payload.message_id)
        stars = len(u async for u in reaction.users() if u.id not in [self.bot.user.id, message.author.id])

        if row is not None:
            hof_channel = self.bot.get_channel(row['hof_channel_id'])
            hof_msg = await hof_channel.fetch_message(row['hof_id'])
            embed = hof_msg.embeds[0]
            fill_embed(embed, 'stars', stars)
            await hof_msg.edit(embed=embed)
            query = 'UPDATE arthof SET stars = ? WHERE original_id = ?'
            await self.bot.db.execute(query, stars, payload.message_id)
            return 
        
        if stars < THRESHOLD:
            return
        
        embed = self.bot.embeds['hof'].copy()
        if len(message.attachments) > 0:
            embed.set_image(url=message.attachments[0].url)
        fill_embed(embed, 'mention', message.author.mention)
        fill_embed(embed, 'messagelink', message.jump_url)
        fill_embed(embed, 'text', message.content)
        fill_embed(embed, 'stars', stars)
        hof_channel = self.bot.get_channel(ART_HOF_CHANNEL_ID)
        hof_msg = await hof_channel.send(embed=embed)
        query = 'INSERT INTO arthof(original_id, hof_id, hof_channel_id, author_id, stars) VALUES(?, ?, ?, ?, ?)'
        await self.bot.db.execute(query, payload.message_id, hof_msg.id, hof_channel.id, message.author.id, stars)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.channel_id not in ART_CHANNEL_IDS:
            return
        
        if str(payload.emoji) != self.bot.vars.get('artHofEmote'):
            return 

        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if message.author.id == payload.user_id:
            return
        reaction = discord.utils.get(message.reactions, emoji=payload.emoji)
        stars = len(u async for u in reaction.users() if u.id not in [self.bot.user.id, message.author.id])

        query = 'SELECT * FROM arthof WHERE original_id = ?' 
        row = await self.bot.db.fetchrow(query, payload.message_id)

        if row is not None:
            hof_channel = self.bot.get_channel(row['hof_channel_id'])
            hof_msg = await hof_channel.fetch_message(row['hof_id'])
            embed = hof_msg.embeds[0]
            fill_embed(embed, 'stars', stars)
            await hof_msg.edit(embed=embed)
            query = 'UPDATE arthof SET stars = ? WHERE original_id = ?'
            await self.bot.db.execute(query, stars, payload.message_id)
            return 


async def setup(bot):
    await bot.add_cog(ArtHof(bot))
