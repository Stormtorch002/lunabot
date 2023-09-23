from discord.ext import commands 
import time 
import json
import discord  
import datetime


class BumpRemind(commands.Cog):

    def __init__(self, bot):
        self.bot = bot 
        with open('embeds.json') as f:
            self.embed = json.load(f)['bump_remind']
        self.channel_id = 899112780840468561
        self.disboard_id = 302050872383242240
 
    async def cog_load(self):
        query = 'SELECT nextbump FROM bumpremind'
        val = await self.bot.db.fetchval(query)
        if val:
            if val > time.time():
                end_time = datetime.datetime.fromtimestamp(val)
                self.bot.loop.create_task(self.task(end_time))
            else:
                await self.send()

    async def send(self):
        channel = self.bot.get_channel(self.channel_id)
        await channel.send(
            '⁺﹒<@&1137968018270457957>﹗𖹭﹒⁺',
            embed=self.embed
        )

    async def task(self, end_time):
        query = 'UPDATE bumpremind SET nextbump = ?'
        await self.bot.db.execute(query, end_time.timestamp())
        await discord.utils.sleep_until(end_time)
        await self.send()

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.id == self.disboard_id:
            if msg.embeds:
                embed = msg.embeds[0]
                if 'Bump done!' in embed.description:
                    end_time = discord.utils.utcnow() + datetime.timedelta(hours=2)
                    self.bot.loop.create_task(self.task(end_time))



async def setup(bot):
    await bot.add_cog(BumpRemind(bot))
