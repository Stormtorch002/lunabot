import discord 
import asyncio 
from discord.ext import commands 
from typing import Literal, Optional
from config import TOKEN
import aiohttp

discord.utils.setup_logging()

STORCH_ID = 718475543061987329

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, status=discord.Status.idle)


async def start():
    print('Loading...')
    await bot.wait_until_ready()
    print('Ready')
    bot.session = aiohttp.ClientSession()
    await bot.load_extension("jishaku")
    await bot.load_extension('db')
    await bot.load_extension("ticket")
    await bot.load_extension("eh")
    await bot.load_extension("help")
    await bot.load_extension("tools")
    await bot.load_extension("autoresponder")
    await bot.load_extension("bdays")
    await bot.load_extension("events")
    await bot.load_extension("embeds")
    await bot.load_extension("rr")
    await bot.load_extension("automsg")
    await bot.load_extension("levels")
    await bot.load_extension('misc')
    await bot.load_extension('bumpremind')
    await bot.load_extension('pingonjoin')

@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


async def main():
    async with bot:
        bot.owner_ids = [STORCH_ID]
        bot.owner_id = STORCH_ID
        bot.STORCH_ID = bot.owner_id
        bot.loop.create_task(start())
        await bot.start(TOKEN)

asyncio.run(main())

