from discord.ext import commands
import json 
import random 
import discord 


class Misc(commands.Cog):

    def __init__(self, bot):
        self.bot = bot 

        with open('topics.json') as f:
            self.topics = json.load(f)
        with open('embeds.json') as f:
            self.embedjson = json.load(f)['topic']

    
    @commands.hybrid_command()
    async def topic(self, ctx):
        embed = discord.Embed.from_dict(self.embedjson)
        embed.description = embed.description.replace('{q}', random.choice(self.topics))
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Misc(bot))
