from discord.ext import commands, tasks
from pytz import timezone
from datetime import datetime, timedelta, date
from datetime import time as dtime, timezone as dtz
import discord
import json
import time
import random
from aiotrivia import TriviaClient
import asyncio
import traceback
import aiosqlite3
from parsedatetime import Calendar

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
    723664045294485634: 'aquamarine'
}
CHANNELS = {
    725093929481142292: ('cerulean', 'aquamarine'),
    782338681083396096: ('aquamarine',),
    782338575106048050: ('cerulean',)
}


class Gigavent(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.start = datetime(2020, 12, 1).astimezone(timezone('US/Eastern'))
        self.last_cerulean = 0
        self.last_aqua = 0
        self.trivia = TriviaClient()

        with open('./cogs/gigavent.json') as f:
            self.points = json.load(f)

        #  self.bot.loop.create_task(self.announce())
        self.general_id = 725093929481142292
        self.pog = '<:pog:763411517197910112>'
        self.counter = 0
        self.boost = {}
        self.db = None
        self.lifebindings = {}
        self.bot.loop.run_until_complete(self.bruh())
        self.bot.loop.create_task(self.insert_points())
        self.remove_lifebindings.start()
        self.pdt = Calendar()
        self.previous_ts = 0

    @tasks.loop(minutes=1)
    async def remove_lifebindings(self):
        query = 'SELECT other_id FROM lifebinding WHERE exp < ?'
        async with self.db.cursor() as cur:
            await cur.execute(query, (int(time.time()),))
            res = await cur.fetchall()
            if res:
                for r in res:
                    query = 'DELETE FROM lifebinding WHERE other_id = ?'
                    await cur.execute(query, (r[0],))
                    if r[0] in self.lifebindings:
                        self.lifebindings.pop(r[0])
                    await self.db.commit()

    def cog_unload(self):
        with open('./cogs/gigavent.json', 'w') as f:
            json.dump(self.points, f)
        self.remove_lifebindings.cancel()

    async def bruh(self):
        self.db = await aiosqlite3.connect('./cogs/gigavent.db')
        self.bot.gigavent_db = self.db
        query = 'CREATE TABLE IF NOT EXISTS lifebinding (user_id INTEGER, other_id INTEGER, exp INTEGER)'
        query2 = 'CREATE TABLE IF NOT EXISTS points (user_id INTEGER, total INTEGER, time INTEGER, team TEXT)'
        async with self.db.cursor() as cur:
            await cur.execute(query)
            await cur.execute(query2)
            await self.db.commit()
            await cur.execute('SELECT * FROM lifebinding')
            res = await cur.fetchall()
            for res in res:
                self.lifebindings[res[1]] = {'claimed': res[0], 'exp': res[2]}

    async def insert_points(self):
        while True:
            now = datetime.now(dtz.utc)
            nxt = datetime.combine(now.date(), dtime(now.hour, now.minute, 0)) + timedelta(minutes=1)
            t = nxt.timestamp()
            if t == self.previous_ts:
                await asyncio.sleep(5)
                continue
            await discord.utils.sleep_until(nxt)
            query = 'INSERT INTO points (user_id, team, total, time) VALUES (?, ?, ?, ?)'
            async with self.db.cursor() as cur:
                for u, team in USERS.items():
                    await cur.execute(query, (u, team, self.points[team][str(u)], t))
            await self.db.commit()
            self.previous_ts = t

    async def announce(self):
        while True:
            dt = datetime.combine(date.today() + timedelta(days=1), dtime(0, 0, 0))
            now = datetime.now().astimezone()
            nh = datetime.combine(now.date(), dtime(now.hour, 0, 0)) + timedelta(hours=1)
            await discord.utils.sleep_until(dt)
            ch = self.bot.get_channel(724743508258324560)
            cerulean = self.points['cerulean']
            aqua = self.points['aquamarine']
            cerulean_t = sum(list(cerulean.values()))
            aqua_t = sum(list(aqua.values()))
            embed = discord.Embed(
                title='Daily Gigavent Results',
                color=discord.Colour.blue()
            ).add_field(
                name='Team Cerulean',
                value='\n'.join(f'{self.bot.get_user(int(user_id)).mention}: `{cerulean[user_id]}`'
                                for user_id in cerulean) + f'\n\n**TOTAL:** `{cerulean_t}`'
            ).add_field(
                name='Team Aquamarine',
                value='\n'.join(f'{self.bot.get_user(int(user_id)).mention}: `{aqua[user_id]}`'
                                for user_id in aqua) + f'\n\n**TOTAL:** `{aqua_t}`'
            )
            await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_point_gain(self, member, gain):
        if member.id in self.lifebindings:
            b = self.lifebindings[member.id]
            member = b['claimed']
            team = USERS[member]
            self.points[team][str(member)] += gain

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id in USERS and message.channel.id in CHANNELS:
            if message.author.id in self.boost:
                multiplier = self.boost
            else:
                multiplier = 1
            team = USERS[message.author.id]
            if team in CHANNELS[message.channel.id]:
                gain = 2 * multiplier
                self.points[team][str(message.author.id)] += gain
                self.bot.dispatch('point_gain', message.author, gain)
            if team == 'cerulean':
                self.last_cerulean = time.time()
            else:
                self.last_aqua = time.time()
            self.counter += 1
            if self.counter == 25:
                self.counter = 0
                if time.time() - self.last_cerulean < 180 and time.time() - self.last_aqua < 180:
                    general = self.bot.get_channel(self.general_id)
                    spawn = random.choice([True, False])
                    if spawn:
                        present = random.choice([True, False, False])
                        if present:
                            msg = await general.send('**:gift: CHRISTMAS GIFT! :gift:**\n\n'
                                                     ':snowflake: First team member to react to the gift box below will receive a random amount of points from 75 to 150. Merry Crysler!')
                            await msg.add_reaction('\U0001f381')

                            def check(p):
                                return str(p.emoji) == '\U0001f381' and p.user_id in USERS and p.message_id == msg.id

                            try:
                                payload = await self.bot.wait_for('raw_reaction_add', timeout=3600, check=check)
                            except asyncio.TimeoutError:
                                await msg.edit(content='Powerup expired.')
                                return
                            await msg.delete()
                            team = USERS[payload.user_id]
                            gain = random.randint(75, 150)
                            self.points[team][str(payload.user_id)] += gain
                            self.bot.dispatch('point_gain', payload.member, gain)
                            await general.send(f':christmas_tree: {payload.member.mention} opened a Christmas Present and received **{gain}** points! '
                                               f':gift:')
                            return
                        n = random.randint(1, 100)
                        if n <= 42:
                            msg = await general.send('**Powerup: ROULETTE!**\n\nFirst team member to react to '
                                                     'the pogchamp below has a 50% chance of gaining 150 points, '
                                                     'and 50% chance of losing 100 points.')
                            await msg.add_reaction(self.pog)

                            def check(p):
                                return str(p.emoji) == self.pog and p.user_id in USERS and p.message_id == msg.id

                            try:
                                payload = await self.bot.wait_for('raw_reaction_add', timeout=3600, check=check)
                            except asyncio.TimeoutError:
                                await msg.edit(content='Powerup expired.')
                                return
                            await msg.delete()
                            win = random.choice([True, False])
                            team = USERS[payload.user_id]

                            if win:
                                self.points[team][str(payload.user_id)] += 100
                                self.bot.dispatch('point_gain', payload.member, 100)
                                await general.send(f'{payload.member.mention} won 100 points for '
                                                   f'**Team {team.capitalize()}**!')
                            else:
                                self.points[team][str(payload.user_id)] -= 100
                                await general.send(f'{payload.member.mention} lost 100 points from '
                                                   f'**Team {team.capitalize()}**...')
                        elif 43 <= n <= 84:
                            try:
                                ques = await self.trivia.get_random_question('medium')
                                m = await general.send('**Powerup: JEOPARDY!**\n\nClick the pogchamp below to '
                                                       'get a trivia question. '
                                                       'Answering correctly will award your team 150 points.')
                                await m.add_reaction(self.pog)

                                def check(p):
                                    return str(p.emoji) == self.pog and p.user_id in USERS and p.message_id == m.id

                                try:
                                    payload = await self.bot.wait_for('raw_reaction_add', timeout=3600, check=check)
                                except asyncio.TimeoutError:
                                    await m.edit(content='Powerup expired.')
                                    return
                                await m.delete()
                                answers = ques.responses
                                letters = {}
                                for i in range(len(answers)):
                                    letters[chr(i + ord('a'))] = answers[i]
                                text = '\n'.join(f'{l.upper()}) {a}' for l, a in letters.items())
                                await general.send(
                                    f'Ok, {payload.member.mention}, you have **20 seconds** to answer:\n\n'
                                    f'*{ques.question}\n\n{text}*')

                                def check(m):
                                    return m.author.id == payload.user_id and m.content.lower() in 'abcd' \
                                           and m.channel.id == general.id
                                try:
                                    msg = await self.bot.wait_for('message', timeout=20, check=check)
                                except asyncio.TimeoutError:
                                    await general.send("Time's up and you didn't answer.")
                                    return

                                if letters[msg.content.lower()] == ques.answer:
                                    team = USERS[payload.user_id]
                                    self.points[team][str(payload.user_id)] += 150
                                    self.bot.dispatch('point_gain', payload.member, 150)
                                    await general.send(f'**CORRECT!** {payload.member.mention} won 150 points for '
                                                       f'**Team {team.capitalize()}**!')
                                else:
                                    await general.send(f'**INCORRECT!** The correct answer was: `{ques.answer}`.')
                            except Exception as e:
                                await general.send(''.join(traceback.format_exception(type(e), e, e.__traceback__)))

                        elif 85 <= n <= 94:
                            m = await general.send('**Powerup: SABOTAGE!**\n\nClick the pogchamp below to '
                                                   'remove 150 points from a random player on the other team.')
                            await m.add_reaction(self.pog)

                            def check(p):
                                return str(p.emoji) == self.pog and p.user_id in USERS and p.message_id == m.id

                            try:
                                payload = await self.bot.wait_for('raw_reaction_add', timeout=3600, check=check)
                            except asyncio.TimeoutError:
                                await m.edit(content='Powerup expired.')
                                return
                            await m.delete()
                            team = USERS[payload.user_id]
                            opp = random.choice([u_id for u_id in USERS if USERS[u_id] != team])
                            opp_team = USERS[opp]
                            member = self.bot.get_user(opp)
                            self.points[opp_team][str(opp)] -= 150
                            await general.send('<:cyan_kill:763418184962670633><:blue_killed:763418185042755695> '
                                               f'{member.mention} was sabotaged by `{payload.member}` and lost 150 points on '
                                               f'Team {opp_team.capitalize()}.')

                        elif 95 <= n <= 99:
                            m = await general.send('**Powerup: BOOSTING!**\n\nClick the pogchamp below to '
                                                   'gain 2x as many points from chatting for the next 10 minutes.')
                            await m.add_reaction(self.pog)

                            def check(p):
                                return str(p.emoji) == self.pog and p.user_id in USERS and p.message_id == m.id

                            try:
                                payload = await self.bot.wait_for('raw_reaction_add', timeout=3600, check=check)
                            except asyncio.TimeoutError:
                                await m.edit(content='Powerup expired.')
                                return
                            await m.delete()
                            if payload.user_id in self.boost:
                                self.boost[payload.user_id] *= 2
                            else:
                                self.boost[payload.user_id] = 2
                            await general.send(f'Congrats to {payload.member.mention}! They received the boost.')
                            await asyncio.sleep(600)
                            self.boost[payload.user_id] /= 2
                        else:
                            m = await general.send('**Powerup: LIFE-BINDING!**\n\nClick the pogchamp below to '
                                                   'claim the **rarest powerup of the event**.')
                            await m.add_reaction(self.pog)

                            def check(p):
                                return str(p.emoji) == self.pog and p.user_id in USERS and p.message_id == m.id

                            try:
                                payload = await self.bot.wait_for('raw_reaction_add', timeout=3600, check=check)
                            except asyncio.TimeoutError:
                                await m.edit(content='Powerup expired.')
                                return
                            await m.delete()
                            team = USERS[payload.user_id]
                            opp = random.choice([u_id for u_id in USERS if USERS[u_id] != team])
                            member = self.bot.get_user(opp)
                            exp = int(time.time() + 6 * 3600)
                            query = 'INSERT INTO lifebinding (user_id, other_id, exp) VALUES (?, ?, ?)'
                            async with self.db.cursor() as cur:
                                await cur.execute(query, (payload.user_id, opp, exp))
                            await self.db.commit()
                            self.lifebindings[opp] = {'claimed': payload.user_id, 'exp': exp}
                            await general.send(f'{payload.member.mention} claimed the rare **TOKEN OF LIFE BINDING** '
                                               f'just in the nick of time! Unfortunately for {member.mention}, '
                                               f'every point they earn now for the next 6 hours will '
                                               f'be reimbursed to the claimer.')
                            await asyncio.sleep(6 * 3600)
                            self.lifebindings.pop(opp)

    @commands.command()
    async def gigavent(self, ctx):
        cerulean = self.points['cerulean']
        aqua = self.points['aquamarine']
        cerulean_t = sum(list(cerulean.values()))
        aqua_t = sum(list(aqua.values()))
        gap = abs(cerulean_t - aqua_t)
        embed = discord.Embed(
            title='Current Gigavent Standings',
            color=discord.Colour.blue()
        ).add_field(
            name='Team Cerulean',
            value='\n'.join(f'<@{user_id}> `{cerulean[user_id]}`'
                            for user_id in cerulean)
                  + f'\n\n**TOTAL:** `{cerulean_t}`'

        ).add_field(
            name='Team Aquamarine',
            value='\n'.join(f'<@{user_id}> `{str(aqua[user_id])}`'
                            for user_id in aqua) + f'\n\n**TOTAL:** `{aqua_t}`'
        ).set_footer(
            text=f'Gap: {gap}'
        )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Gigavent(bot))
