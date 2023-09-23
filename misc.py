from discord.ext import commands
import json 
import random 


class Misc(commands.Cog):

    def __init__(self, bot):
        self.bot = bot 

        with open('topics.json') as f:
            self.topics = json.load(f)

    
    @commands.hybrid_command()
    async def topic(self, ctx):
        await ctx.send(f'> {random.choice(self.topics)}')


async def setup(bot):
    await bot.add_cog(Misc(bot))
