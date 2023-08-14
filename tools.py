from discord.ext import commands 
import json 
from discord import ui 
from discord.utils import escape_markdown
from embed_editor.editor import EmbedEditor


class Tools(commands.Cog, description='storchs tools'):
    
    def __init__(self, bot):
        self.bot = bot 

    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator or ctx.author.id == self.bot.owner_id

    @commands.command()
    async def buildembed(self, ctx):
        view = EmbedEditor(self.bot, ctx.author, timeout=None)
        await ctx.send('Please hit the **Submit** button when you\'re ready!', view=view)
        await view.wait()
        if view.ready:
            await ctx.send(embed=view.current_embed)
        

    @commands.command()
    async def grabembed(self, ctx, url):
        tokens = url.split('/')
        channel_id = int(tokens[5])
        message_id = int(tokens[6])
        channel = self.bot.get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        embed = message.embeds[0].to_dict()

        if 'footer' in embed:
            embed.pop('footer')
            
        data = json.dumps(embed, indent=4)
        await ctx.send(f'```json\n{data}```')

    @commands.command()
    async def grabbuttonemoji(self, ctx, url):
        tokens = url.split('/')
        channel_id = int(tokens[5])
        message_id = int(tokens[6])
        channel = self.bot.get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        view = ui.View.from_message(message)
        await ctx.send(escape_markdown(str(view.children[0].emoji)))

async def setup(bot):
    await bot.add_cog(Tools(bot))