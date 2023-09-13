import discord 
import asyncio 
from discord.ext import commands 


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
    await bot.load_extension("jishaku")
    await bot.load_extension("tools")
    await bot.load_extension("ticket")


async def main():
    async with bot:
        bot.owner_ids = [STORCH_ID]
        bot.owner_id = STORCH_ID
        bot.loop.create_task(start())
        await bot.start('MTEyNzExMDQ5NzAyODgwODcwNQ.Gzh-i4.api6WQbLlWCEOlVf6j2zqaA-t5xO8XFzgW6Kzg')

asyncio.run(main())

