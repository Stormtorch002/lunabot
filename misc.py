from discord.ext import commands
import json 
import random 
import discord 
import asyncio 


class Misc(commands.Cog):

    def __init__(self, bot):
        self.bot = bot 

        with open('topics.json') as f:
            self.topics = json.load(f)
        with open('embeds.json') as f:
            self.embedjson = json.load(f)['topic']
        with open('webhooks.json') as f:
            self.webhooks = json.load(f)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        name = member.display_name
        if len(name) > 28:
            name = name[:28]
        await asyncio.sleep(1)
        await member.edit(nick=f'✿❀﹕{name}﹕')
    
    @commands.hybrid_command()
    async def topic(self, ctx):
        embed = discord.Embed.from_dict(self.embedjson)
        embed.description = embed.description.replace('{q}', random.choice(self.topics))
        await ctx.send(embed=embed)
    
    @commands.hybrid_command()
    async def polyjuice(self, ctx, member: discord.Member, *, sentence: str):
        if ctx.channel.id not in self.webhooks:
            webhook = await ctx.channel.create_webhook(name='polyjuice')
            self.webhooks[ctx.channel.id] = webhook.url
            with open('webhooks.json', 'w') as f:
                json.dump(self.webhooks, f)
        else:
            webhook = discord.Webhook.from_url(self.webhooks[ctx.channel.id], session=self.bot.session)
        if ctx.interaction is None:
            await ctx.message.delete()
        else:
            await ctx.interaction.response.defer()
        await webhook.send(sentence, username=member.display_name, avatar_url=member.display_avatar.url)
        


async def setup(bot):
    await bot.add_cog(Misc(bot))
