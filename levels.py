from discord.ext import commands, tasks
import json 
from num2words import num2words
from io import BytesIO
from utils.image import generate_rank_card
from utils.views import RoboPages, AutoSource
import time
import random
import discord
import datetime
import math


def get_xp(lvl: int):
    return 50*lvl*lvl 


def get_level(xp: int):
    return int(math.sqrt(xp / 50))


class Levels(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.xp_cooldowns = {}
        self.leveled_roles = {
            1: 938858105473740840,
            5: 923096157645852693,
            10: 923096156324646922,
            15: 923096155460603984,
            20: 923096300696793128,
            25: 923096335039746048,
            30: 923096337841520721,
            40: 923096336436432996,
            50: 923096766805590026,
            75: 923096798078324756,
            100: 923096803958747187
        }
        self.blacklisted_channels = [
            899112780840468561,
            1093318315792945243,
            899119063496785950,
            899119100536705084,
            1023276761087234098,
            1073847932828258384,
            964728745451728946,
            933877494598225930,
            1096583202254110761,
            1104219541992648764,
            1104219647663931453,
            1106805421630574612,
            1106805666997358623,
            1106805702619578518 ,
            1106819476093149274,
            899513989061554257
        ]
        self.xp_multipliers = {
            913086743035658292: 1.2,
            1060750259980079195: 1.15,
            981252193132884109: 1.1
        }
        self.xp_cache = {} 
        self.msg_counts = {}
        self.weekly_xp_task.start()

    # make a loop that runs every sunday at 1am 
    async def weekly_xp(self):
        query = '''SELECT xp.user_id, (xp.total_xp - xp_copy.total_xp) AS diff
                    FROM xp
                    INNER JOIN xp_copy ON xp.user_id = xp_copy.user_id
                    ORDER BY diff DESC
                    LIMIT 3;
                '''
        rows = await self.bot.db.fetch(query)
    

        with open('embeds.json', encoding='utf8') as f:
            data = json.load(f)
        
        embed = discord.Embed.from_dict(data['weekly_xp'])

        for i in range(3):
            msgs = self.msg_counts[rows[i][0]]
            embed.description = embed.description.replace(f'{{ping}}{i}', f'<@{rows[i][0]}>')
            embed.description = embed.description.replace(f'{{xp}}{i}', f'{rows[i][1]}')
            embed.description = embed.description.replace(f'{{msgs}}{i}', f'{msgs}')
        
        embed2 = discord.Embed.from_dict(data['weekly_reset'])
        this_sunday = discord.utils.utcnow()
        next_sunday = this_sunday + datetime.timedelta(days=7)
        embed2.description = embed2.description.replace('{this_sunday}', discord.utils.format_dt(this_sunday, 'd'))
        embed2.description = embed2.description.replace('{next_sunday}', discord.utils.format_dt(next_sunday, 'd'))

        channel = self.bot.get_channel(899725913586032701)
        await channel.send(embed)
        await channel.send(embed2)
        
        await self.freeze_lb()

    @tasks.loop(hours=168)
    async def weekly_xp_task(self):
        await self.weekly_xp()
        # select top 3 users order by the difference between xp and xp_copy 
            
    @weekly_xp_task.before_loop
    async def before_weekly_xp(self):
        # sleep until next sunday at 1am
        now = datetime.datetime.now()
        if now.hour == 0:
            target = now.replace(hour=1, minute=0, second=0, microsecond=0)
        else:
            target = now.replace(hour=1, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        while target.weekday() != 6:
            target += datetime.timedelta(days=1)
        await discord.utils.sleep_until(target)

    async def cog_load(self):
        query = 'select user_id, total_xp from xp'
        rows = await self.bot.db.fetch(query)
        for row in rows:
            self.xp_cache[row[0]] = row[1]
        rows = await self.bot.db.fetch('select user_id, count from msg_count')
        for row in rows:
            self.msg_counts[row[0]] = row[1]

    async def cog_unload(self):
        for user_id, total_xp in self.xp_cache.items():
            query = '''INSERT INTO xp (user_id, "total_xp") 
                        VALUES (?, ?)
                        ON CONFLICT (user_id)
                        DO UPDATE SET total_xp = ? 
                    '''
            await self.bot.db.execute(query, user_id, total_xp, total_xp) 
        for user_id, count in self.msg_counts.items():
            query = '''INSERT INTO msg_count (user_id, count) 
                        VALUES (?, ?)
                        ON CONFLICT (user_id)
                        DO UPDATE SET count = ? 
                    '''
            await self.bot.db.execute(query, user_id, count, count)
    
    async def freeze_lb(self):
        await self.bot.db.execute('DROP TABLE IF EXISTS xp_copy')
        # make a copy of the xp table
        await self.bot.db.execute('CREATE TABLE xp_copy AS SELECT * FROM xp')
        await self.bot.db.execute('DROP TABLE IF EXISTS msg_count')
        await self.bot.db.execute('CREATE TABLE msg_count (user_id INTEGER PRIMARY KEY, count INTEGER)')
        self.msg_counts = {}

    async def add_leveled_roles(self, message, old_level, new_level, authorroles):
        roles = {lvl: self.leveled_roles[lvl] for lvl in self.leveled_roles if lvl <= new_level}
        if roles:
            keys = list(roles.keys())
            lvl = max(keys)
            role = roles[lvl]
            keys.remove(lvl)
            if role not in authorroles:
                role = message.guild.get_role(role)
                await message.author.add_roles(role)
            for lvl in keys:
                role = roles[lvl]
                if role in authorroles:
                    role = message.guild.get_role(role)
                    await message.author.remove_roles(role)

        if old_level != new_level:
            embed = discord.Embed(title='❀ㆍㆍLevel Up﹗⁺ ₍ <a:LC_lilac_heart_NF2U_DNS:1046191564055138365> ₎', color=0xcab7ff)
            embed.description = f'> ♡﹒﹒**Psst!** Tysm for being active here with us, you are now level {new_level}. Keep sending messages to gain more levels, which can gain you some **epic perks**. Tired of receiving these level up messages?? Go [here](https://discord.com/channels/899108709450543115/1106225161562230925) to remove access to this channel; just react to that message again to regain access. <a:LC_star_burst:1147790893064142989> ✿❀'
            embed.set_footer(text='⁺﹒Type ".myperks" to view our full list of available perks, including perks for our active members﹒⁺')
            channel = self.bot.get_channel(1137942143562940436)
            await channel.send(f'⁺﹒{message.author.mention}﹗𖹭﹒⁺', embed=embed)

        self.xp_cooldowns[message.author.id] = time.time() + 15

    async def get_xp_info(self, user):
        query = """SELECT (
                       SELECT COUNT(*)
                       FROM xp second
                       WHERE second.total_xp >= first.total_xp
                   ) AS rank, total_xp 
                   FROM xp first
                   WHERE user_id = $1
                """
        res = await self.bot.db.fetchrow(query, user.id)
        return res

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.channel.id not in self.blacklisted_channels and not message.author.bot:
            self.msg_counts[message.author.id] = self.msg_counts.get(message.author.id, 0) + 1

            if message.author.id not in self.xp_cooldowns or self.xp_cooldowns[message.author.id] < time.time():
                authorroles = [role.id for role in message.author.roles]
                increment = random.randint(20, 25)
                for role_id, multi in self.xp_multipliers.items():
                    if role_id in authorroles:
                        increment *= multi 
                increment = round(increment)
                old = self.xp_cache.get(message.author.id)
                if old is None:
                    self.xp_cache[message.author.id] = increment 
                    new = increment
                    old = 0
                else:
                    self.xp_cache[message.author.id] += increment
                    new = old + increment 
                new_level, old_level = get_level(new), get_level(old)
                await self.add_leveled_roles(message, old_level, new_level, authorroles)

    @commands.hybrid_command(name='rank')
    async def _rank(self, ctx, *, member: discord.Member = None):
        """Checks your server level and XP and other stats"""

        m = member if member else ctx.author

        async with ctx.channel.typing():

            xp = self.xp_cache.get(m.id)
            if xp is None:
                self.xp_cache[ctx.author.id] = 0
                xp = 0

            rank = len([v for v in self.xp_cache.values() if v > xp]) + 1
            mx = xp
            current_level = get_level(mx)

            empty = get_xp(current_level)
            full = get_xp(current_level+1)
            pc = (mx - empty) / (full - empty)

            nlr = nl = None
            av_file = BytesIO()
            await m.display_avatar.with_format('png').save(av_file)

            t1 = time.perf_counter()
            file = await self.bot.loop.run_in_executor(None, generate_rank_card, current_level, av_file, pc)
            t2 = time.perf_counter()

            embed = discord.Embed(title='❀ㆍㆍYour Rank﹗⁺ ₍ <a:LCD_flower_spin:1147757953064128512> ₎', color=0xcab7ff)
            embed.description = (f'''
> ⁺ <a:Lumi_arrow_R:927733713163403344>﹒__Rank__ :: {num2words(rank, to='ordinal_num')}﹒⁺
> ⁺ <a:Lumi_arrow_R:927733713163403344>﹒__XP__ :: {xp}﹒⁺
> ⁺ <a:Lumi_arrow_R:927733713163403344>﹒__Needed XP__ :: {full - mx}﹒⁺')
            ''')
            embed.set_footer(text='⁺﹒Type ".myperks" to view our full list of available perks, including perks for our active members﹒⁺')
            embed.set_image(url='attachment://rank.gif')
            total = t2 - t1 
            await ctx.send(f'Render time: `{round(total, 3)}s`', embed=embed, file=discord.File(fp=file, filename='rank.gif'))


    @commands.command(aliases=['leaaderboard'])
    async def lb(self, ctx):
        """Shows the XP leaderboard."""

        res = sorted(self.xp_cache.items(), key=lambda x: x[1], reverse=True)

        i = 0
        while i < len(res):
            row = res[i]
            temp = ctx.guild.get_member(row[0])
            if temp is None:
                res.pop(i)
            else:
                i += 1

        chunks = [res[i:i + 12] for i in range(0, len(res), 12)]
        pages = len(chunks)
        embeds = []
        page = 1
        rank = 1 

        for rows in chunks:
            
            embed = discord.Embed(title=f'Leaderboard', color=ctx.author.color)
            embed.set_author(name=f'Page {page}', icon_url=str(ctx.guild.icon.with_format('png')))
            embed.set_footer(text=f'Page {page}/{pages}')

            for row in rows:
                member, xp = ctx.guild.get_member(row[0]), row[1]
                lvl, name = get_level(xp), f'#{rank}'

                value = f'{member.mention}\n**Level:** `{lvl}`\n**Total XP:** `{xp}`'
                embed.add_field(name=name, value=value)
#                 else:
                    # member_id = row['user_id']
                    # name = f'#{rank} (Member Left Server)'
                    # member = f'<@{member_id}>'
                    # value = f'{member}\n**Level:** `{lvl}`\n**Total XP:** `{xp}`'
                    # embed.add_field(name=name, value=value)
                rank += 1
            page += 1
            embeds.append(embed)

        view = RoboPages(AutoSource(embeds, per_page=1), ctx=ctx)
        await view.start() 



async def setup(bot):
    await bot.add_cog(Levels(bot))
