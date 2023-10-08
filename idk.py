from discord.ext import commands, flags
import discord
import time
import matplotlib.pyplot as plt
from pytz import timezone
from io import BytesIO
import aiohttp
from urllib.parse import urlencode
import asyncio
import json
from datetime import datetime
import matplotlib.dates

USERS = {
    553058885418876928: 'cerulean',
    687661271989878860: 'cerulean',
    576187414033334282: 'cerulean',
    726973610119397448: 'cerulean',
    713581361809719307: 'cerulean',
    543942843664957443: 'cerulean',
    426110953021505549: 'cerulean',
    376171072422281236: 'aquamarine',
    642754388988788761: 'aquamarine',
    704815193590464592: 'aquamarine',
    496225545529327616: 'aquamarine',
    715930391747231754: 'aquamarine',
    774749560424628245: 'aquamarine'
}


def setup(bot):
    self = bot.get_cog('Gigavent')

    @bot.command()
    async def call(ctx, *, number):
        url = 'https://some-random-api.ml/chatbot?'
        await ctx.send(f'**{number}** `How may I help you?`')
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    msg = await bot.wait_for('message',
                                             check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                                             timeout=30)
                except asyncio.TimeoutError:
                    return await ctx.send('**CALL ENDED.**')

                async with session.get(url + urlencode({'message': msg.content})) as resp:
                    r = (await resp.json())['response']
                    await ctx.send(f'`{r}`')

    @flags.command()
    @flags.add_flag('--users', nargs='+')
    @flags.add_flag('--start', default=['12/01', '00:00'], nargs='+')
    @flags.add_flag('--end', default=['boomer'], nargs='+')
    async def chart(ctx, **options):
        tz = timezone('US/Eastern')
        low, high = ' '.join(options['start']), ' '.join(options['end'])
        if high == 'boomer':
            high = datetime.now().astimezone(tz).strftime('%m/%d %H:%M')
        high += ' y=2020'
        low += ' y=2020'
        high, low = datetime.strptime(high, '%m/%d %H:%M y=%Y').replace(tzinfo=tz), \
                    datetime.strptime(low, '%m/%d %H:%M y=%Y').replace(tzinfo=tz)
        print(str(high), str(low))
        l_ts, h_ts = low.timestamp(), high.timestamp()
        users = ' '.join(options['users'])
        async with self.db.cursor() as cur:
            if users == 'aquamarine only':
                print(l_ts, h_ts)
                await cur.execute(
                    'SELECT time, SUM(total) FROM points WHERE team = ? AND time<? AND ?<time GROUP BY time',
                    ('aquamarine', h_ts, l_ts))
                res = await cur.fetchall()
                sums = {res[0]: res[1] for res in res}

                def e():
                    a = [t / 86400 for t in sums]
                    formatter = matplotlib.dates.DateFormatter('%m/%d\n%H:%M', tz=tz)

                    figure = plt.figure()
                    axes = figure.add_subplot(1, 1, 1)

                    axes.xaxis.set_major_formatter(formatter)
                    plt.setp(axes.get_xticklabels(), rotation=15)

                    axes.plot(a, list(sums.values()), color='#7fffd4')
                    buf = BytesIO()
                    figure.savefig(buf, format='png')
                    buf.seek(0)
                    return buf

                b = await self.bot.loop.run_in_executor(None, e)
                await ctx.send(file=discord.File(fp=b, filename='aqua.png'))
            elif users == 'cerulean only':
                print(l_ts, h_ts)
                await cur.execute(
                    'SELECT time, SUM(total) FROM points WHERE team = ? AND time<? AND ?<time GROUP BY time',
                    ('cerulean', h_ts, l_ts))
                res = await cur.fetchall()
                sums = {res[0]: res[1] for res in res}

                def e():
                    a = [t / 86400 for t in sums]
                    formatter = matplotlib.dates.DateFormatter('%m/%d\n%H:%M', tz=tz)

                    figure = plt.figure()
                    axes = figure.add_subplot(1, 1, 1)

                    axes.xaxis.set_major_formatter(formatter)
                    plt.setp(axes.get_xticklabels(), rotation=15)

                    axes.plot(a, list(sums.values()), color='#2a52be')
                    buf = BytesIO()
                    figure.savefig(buf, format='png')
                    buf.seek(0)
                    return buf

                b = await self.bot.loop.run_in_executor(None, e)
                await ctx.send(file=discord.File(fp=b, filename='cerulean.png'))
            elif users == 'both':
                print(l_ts, h_ts)
                await cur.execute(
                    'SELECT time, SUM(total) FROM points WHERE team = ? AND time<? AND ?<time GROUP BY time',
                    ('aquamarine', h_ts, l_ts))
                res = await cur.fetchall()
                aq_sums = {res[0]: res[1] for res in res}
                await cur.execute(
                    'SELECT time, SUM(total) FROM points WHERE team = ? AND time<? AND ?<time GROUP BY time',
                    ('cerulean', h_ts, l_ts))
                res = await cur.fetchall()
                ce_sums = {res[0]: res[1] for res in res}

                def e():
                    a = [t / 86400 for t in aq_sums]
                    formatter = matplotlib.dates.DateFormatter('%m/%d\n%H:%M', tz=tz)

                    figure = plt.figure()
                    axes = figure.add_subplot(1, 1, 1)

                    axes.xaxis.set_major_formatter(formatter)
                    plt.setp(axes.get_xticklabels(), rotation=15)

                    axes.plot(a, list(aq_sums.values()), color='#7fffd4')
                    axes.plot(a, list(ce_sums.values()), color='#2a52be')
                    buf = BytesIO()
                    figure.savefig(buf, format='png')
                    buf.seek(0)
                    return buf

                b = await self.bot.loop.run_in_executor(None, e)
                await ctx.send(file=discord.File(fp=b, filename='aqua.png'))
            elif users == 'aquamarine':
                ids = [u.id]
            est = timezone('US/Eastern')
        fig, ax = plt.subplots(1, 2, figsize=(8, 4))

    bot.add_command(chart)
