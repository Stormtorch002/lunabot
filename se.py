from typing import Optional
from discord.ext import commands, tasks 
import discord 
import time 
import json 
import random 
from discord import ui 
import matplotlib.pyplot as plt
import numpy as np 
import asyncio 
from lunascript import Layout, LunaScript
from trivia import questions


OPTION3_TIME = 30 
OPTION4_TIME = 30 
OPTION5_TIME = 30 
OPTION5_CD = 10 
LOW_PERIOD = 100 
HIGH_PERIOD = 3 
INDIV_REDUCED_CD = 1 
TEAM_REDUCED_CD = 1 
BASE_CD = 3 
INDIV_DOUBLE_TIME = 30 
TEAM_DOUBLE_TIME = 30 
INDIV_TRIPLE_TIME = 15 
TEAM_TRIPLE_TIME = 15 
INDIV_REDUCED_CD_TIME = 30 
TEAM_REDUCED_CD_TIME = 30
WELC_CD = 30 

# OPTION3_TIME = 30 * 60
# OPTION4_TIME = 20 * 60
# OPTION5_TIME = 25 * 60
# OPTION5_CD = 60 
# LOW_PERIOD = 500 
# HIGH_PERIOD = 1000
# INDIV_REDUCED_CD = 60
# TEAM_REDUCED_CD = 120
# BASE_CD = 180
# INDIV_DOUBLE_TIME = 15 * 60
# TEAM_DOUBLE_TIME = 5 * 60
# INDIV_TRIPLE_TIME = 15 * 60
# TEAM_TRIPLE_TIME = 5 * 60
# INDIV_REDUCED_CD_TIME = 30 * 60
# TEAM_REDUCED_CD_TIME = 30 * 60
# WELC_CD = 5 * 60


class RedeemView(ui.View):

    def __init__(self, ctx, choices, powerups):
        super().__init__(timeout=180)
        self.inter = None 
        self.custom_id = None 

        async def callback(inter):
            if inter.user != ctx.author:
                return await inter.response.defer()
            
            self.custom_id = inter.data['custom_id']
            self.inter = inter 
            self.stop()

        for i, choice in enumerate(choices):
            i += 1
            btn = ui.Button(label=str(i), custom_id=str(powerups.index(choice)), style=discord.ButtonStyle.blurple, row=i)
            btn.callback = callback
            self.add_item(btn)
        

class Powerup:
    pass 

class PowerupEffect(Powerup):
    def __init__(self, end):
        self.end = end


class Multiplier(Powerup):
    def __init__(self, n, end):
        super().__init__(end)
        self.n = n 
        self.name = 'Multiplier'
    

class CooldownReducer(Powerup):
    def __init__(self, cd, end):
        super().__init__(end)
        self.n = cd 
        self.name = 'Cooldown Reducer'


class Team:
    def __init__(self, name, players, channel, redeems, saved_powerups):
        self.name = name 
        self.players = players 
        self.channel = channel

        for player in self.players:
            player.team = self

        self.captain = None 
        self.msg_count = 0
        self.redeems = redeems 
        self.saved_powerups = saved_powerups
        self.opp = None 
    
    def create_captain(self):
        self.captain = self.players[0]

    async def on_1000(self):
        self.redeems += 1
        query = 'update redeems set number = number + 1 where team = ?'
        await self.captain.bot.db.execute(query, self.name)
        args = {
            'messages': self.msg_count,
            'captainping': self.captain.member.mention,
        }
        layout = Layout.from_name(self.captain.bot, '1k_private')
        ls = LunaScript.from_layout(self.channel, layout, args=args)
        await ls.send()
    
    async def option1(self):
        points = random.randint(15, 20)
        await self.captain.add_points(points, 'topup_powerup')
        return points
    
    async def option2(self):
        points = random.randint(10, 15)
        await self.opp.captain.remove_points(points, 'stolen')
        await self.captain.add_points(points, 'steal_powerup')
        return points
    
    async def option3(self):
        for player in self.players:
            await player.apply_powerup(Multiplier(2, time.time() + OPTION3_TIME))
        
    async def option4(self):
        for player in self.players:
            await player.apply_powerup(Multiplier(3, time.time() + OPTION4_TIME))
    
    async def option5(self):
        for player in self.players:
            await player.apply_powerup(CooldownReducer(OPTION5_CD, time.time() + OPTION5_TIME))


    @property 
    def total_points(self):
        return sum([player.points for player in self.players])


class Player:

    def __init__(self, bot, team, member, nick, points, msg_count, powerups):
        self.bot = bot 
        self.member = member 
        self.nick = nick 
        self.points = points 
        self.team = team 
        self.cds = [BASE_CD]
        self.multi = 1 
        self.powerups = powerups
        self.next_msg = 0
        self.next_welc = 0
        self.msg_count = msg_count

        self.apply_powerups()
    
    @property
    def cd(self):
        return min(self.cds)

    async def task(self, powerup):
        if isinstance(powerup, Multiplier):
            self.multi *= powerup.n
            await asyncio.sleep(powerup.end - time.time())
            self.multi //= powerup.n 
        elif isinstance(powerup, CooldownReducer):
            self.cds.append(powerup.n)
            await asyncio.sleep(powerup.end - time.time())
            self.cds.remove(powerup.n)

    async def apply_powerup(self, powerup):
        query = 'insert into powerups (user_id, name, value, end_time) values (?, ?, ?, ?)'
        await self.bot.db.execute(query, self.member.id, powerup.name, powerup.n, powerup.end)
        self.bot.loop.create_task(self.task(powerup))

    def apply_powerups(self):
        for powerup in self.powerups:
            self.bot.loop.create_task(self.task(powerup))
            
    async def on_msg(self):
        await self.log_msg()
        if time.time() < self.next_msg:
            return 
        self.next_msg = time.time() + self.cd 
        await self.add_points(1, 'msg')
    
    async def on_welc(self):
        if time.time() < self.next_welc:
            return
        self.next_welc = time.time() + WELC_CD 
        bonus = random.randint(1, 3)
        await self.add_points(bonus, 'welc')
        layout = Layout.from_name(self.bot, 'welc_bonus')
        args = {
            'points': bonus,
            'eventnick': self.nick,
            'teamname': self.team.name,
        }
        ls = LunaScript.from_layout(self.member, layout, args=args)
        await ls.send()

    async def log_msg(self):
        self.msg_count += 1
        self.team.msg_count += 1
        query = 'update se_stats set msgs = msgs + 1 where user_id = ?'
        await self.bot.db.execute(query, self.member.id)
        query = 'insert into se_log (team, user_id, type, gain, time) values (?, ?, ?, ?, ?)'
        await self.bot.db.execute(query, self.team.name, self.member.id, 'msg', 1, int(time.time()))

    async def add_points(self, points, reason, multi=True):
        if multi:
            gain = points * self.multi
        else:
            gain = points

        self.points += gain

        query = 'insert into se_log (team, user_id, type, gain, time) values (?, ?, ?, ?, ?)'
        await self.bot.db.execute(query, self.team.name, self.member.id, reason, gain, int(time.time()))
        query = 'update se_stats set points = points + ? where user_id = ?'
        await self.bot.db.execute(query, gain, self.member.id)
    
    async def remove_points(self, points, reason):
        self.points -= points 
        query = 'insert into se_log (team, user_id, type, gain, time) values (?, ?, ?, ?, ?)'
        await self.bot.db.execute(query, self.team.name, self.member.id, reason, -points, int(time.time()))
        query = 'update se_stats set points = points - ? where team = ?'
        await self.bot.db.execute(query, points, self.member.id)
    
    async def on_500(self):
        await self.add_points(25, '', multi=False)
        args = {
            'messages': self.msg_count,
        }
        layout = Layout.from_name(self.bot, '500_bonus')
        ls = LunaScript.from_layout(self.team.channel, layout, args=args, member=self.member)
        await ls.send()

    

class ServerEvent(commands.Cog):

    def __init__(self, bot):
        self.bot = bot 
        self.teams = {}
        self.players = {}
        self.guild_id = 899108709450543115
        self.general_id = 899725913586032701
        self.channel_ids = {1158930467337293905, 1158931468664446986, self.general_id}
        self.msgs_needed = random.randint(15, 35)
        self.msg_counter = 0 
        self.has_welcomed = set() 

        self.powerups_1k = [
            'Receive 15-20 points',
            'Steal 10-15 points from the other team',
            'Double all incoming points for 30 minutes',
            'Triple all incoming points for 20 minutes',
            'Reduce the cooldown for messages to 1 minute for 25 minutes'
        ]
        self.powerups_chat = [
            'Trivia :: 1 - 5 points',
            'Steal-trivia :: steal 1 - 5 points',
            'Reduced Cooldown',
            'Double Point Multiplier',
            'Triple Point Multiplier'
        ]
    
    def generate_powerup(self):
        n = random.uniform(0, 1)
        if n < 0.5:
            return 0
        elif n < 0.75:
            return 1
        elif n < 0.85:
            return 2
        elif n < 0.95:
            return 3
        else:
            return 4

    async def cog_load(self):

        playerdict = {
            'bunny': [718475543061987329,496225545529327616, ],
            'kitty': [687661271989878860]
        }
        channels = {
            'bunny': 1158930467337293905,
            'kitty': 1158931468664446986
        }
        nicks = {
            496225545529327616: 'Luna',
            687661271989878860: 'Nemi',
            718475543061987329: 'Storch'
        }

        for team, members in playerdict.items():
            query = 'insert into se_stats (user_id, team, points, msgs) values (?, ?, 0, 0) on conflict (user_id) do nothing'
            for member in members:
                await self.bot.db.execute(query, member, team)
            
        rows = await self.bot.db.fetch('select * from se_stats')
        self.guild = self.bot.get_guild(self.guild_id)

        for row in rows:
            member = self.guild.get_member(row['user_id'])
            if member is None:
                continue 
        
            team = row['team']
            if team not in self.teams:
                query = 'insert into redeems (team, number) values (?, 0) on conflict (team) do nothing'
                await self.bot.db.execute(query, team)
                query = 'select number from redeems where team = ?'
                redeems = await self.bot.db.fetchval(query, team)
                query = 'select option from saved_powerups where team = ?'
                saved_powerups = [row['option'] for row in await self.bot.db.fetch(query, team)]
                self.teams[team] = Team(team, [], self.bot.get_channel(channels[team]), redeems, saved_powerups)
            
            query = 'select name, value, end_time from powerups where user_id = ? and end_time > ?'
            rows = await self.bot.db.fetch(query, member.id, time.time())
            powerups = []
            for row in rows:
                if row['name'] == 'Multiplier':
                    powerups.append(Multiplier(row['value'], row['end_time']))
                elif row['name'] == 'Cooldown Reducer':
                    powerups.append(CooldownReducer(row['value'], row['end_time']))

            query = 'select msgs, points from se_stats where user_id = ?'
            row = await self.bot.db.fetchrow(query, member.id)

            team = self.teams[team]
            player = Player(self.bot, team, member, nicks[member.id], row['points'], row['msgs'], powerups)
            self.players[member.id] = player 
            team.players.append(player)
            team.msg_count += player.msg_count

        team1 = self.teams['bunny']
        team2 = self.teams['kitty']
        team1.create_captain()
        team2.create_captain()
        team1.opp = team2
        team2.opp = team1

        self.questions = questions 
        random.shuffle(self.questions)
        self.questions_i = 0


    async def cog_check(self, ctx):
        return ctx.author.id in self.players or ctx.author.id == 718475543061987329

    async def trivia(self, player, channel, steal=False):
        q_tuple = self.questions[self.questions_i]
        q = q_tuple[0]
        a = q_tuple[1]
        choices = q_tuple[2]()
        choices.append(a)
        random.shuffle(choices)
        
        if self.questions_i == len(self.questions) - 1:
            random.shuffle(self.questions)
            self.questions_i = 0
        else:
            self.questions_i += 1

        points = random.randint(1, 5) 
        args = {
            'question': q,
            'ans1': choices[0],
            'ans2': choices[1],
            'ans3': choices[2],
            'ans4': choices[3],
            'points': points,
            'eventnick': player.nick,
            'teamname': player.team.name,
        }
        if not steal:
            layout = Layout.from_name(self.bot, 'trivia')
        else:
            args['otherteamname'] = player.team.opp.name
            layout = Layout.from_name(self.bot, 'steal_trivia')

        ls = LunaScript.from_layout(channel, layout, args=args, member=player.member)
        msg = await ls.send()
        
        emojis = {
            '<:LC_alpha_A_NF2U:1113244739337207909>': 0,
            '<:LC_alpha_B_NF2U:1113244768235958402>': 1,
            '<:LC_alpha_C_NF2U:1113244841275568129>': 2,
            '<:LC_alpha_D_NF2U:1113244889224859660>': 3
        }

        def check(r, u):
            return r.message == msg and u.id == player.member.id and str(r.emoji) in emojis
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=45)
        except asyncio.TimeoutError:
            await msg.delete()
            await channel.send('You did not answer in time!', delete_after=5)
            return
        
        await msg.delete()
        if emojis[str(reaction.emoji)] == choices.index(a):
            if not steal:
                await player.add_points(points, 'trivia')
                await channel.send(f'You got the answer right! You earned **{points}** points.')
            else:
                await player.team.opp.captain.remove_points(points, 'steal_trivia')
                await player.add_points(points, 'steal_trivia')
                await channel.send(f'You got the answer right! You stole **{points}** points from the other team.')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        self.has_welcomed = set()

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.guild is None or msg.guild.id != self.guild_id:
            return 
        if msg.author.bot:
            return 
        if msg.author.id not in self.players:
            return 
        if msg.channel.id not in self.channel_ids:
            return

        player = self.players[msg.author.id]
        await player.on_msg()

        if msg.author.id not in self.has_welcomed:
            if msg.content.lower().startswith('welc'):
                await player.on_welc()

        if player.msg_count % LOW_PERIOD == 0:
            await player.on_500()
        
        if player.team.msg_count % HIGH_PERIOD == 0:
            await player.team.on_1000()
        
        self.msg_counter += 1
        if self.msg_counter >= self.msgs_needed:
            self.msg_counter = 0 
            self.msgs_needed = random.randint(15, 35)
            if random.choice([True, False]):
                layout = Layout.from_name(self.bot, 'powerup_spawn')
                powerup_i = self.generate_powerup()
                powerup_name = self.powerups_chat[powerup_i]
                ls = LunaScript.from_layout(msg.channel, layout, args={'powerupname': powerup_name})
                spawn = await ls.send()
                await spawn.add_reaction('<a:LC_lilac_heart_NF2U_DNS:1046191564055138365>')

                def check(r, u):
                    return u.id in self.players and r.message == spawn and str(r.emoji) == '<a:LC_lilac_heart_NF2U_DNS:1046191564055138365>'

                try:
                    reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=60)
                except asyncio.TimeoutError:
                    await spawn.delete()
                    return 
                
                player = self.players[user.id]
                layout = None 

                if powerup_i == 0:
                    await self.trivia(player, msg.channel)
                elif powerup_i == 1:
                    await self.trivia(player, msg.channel, steal=True)
                elif powerup_i == 2:
                    await player.apply_powerup(CooldownReducer(INDIV_REDUCED_CD, time.time() + INDIV_REDUCED_CD_TIME))

                    for other in player.team.players:
                        if other != player:
                            await other.apply_powerup(CooldownReducer(TEAM_REDUCED_CD, time.time() + TEAM_REDUCED_CD_TIME))

                    layout = Layout.from_name(self.bot, 'reduced_cd')
                elif powerup_i == 3:
                    await player.apply_powerup(Multiplier(2, time.time() + INDIV_DOUBLE_TIME))

                    for other in player.team.players:
                        if other != player:
                            await other.apply_powerup(Multiplier(2, time.time() + TEAM_DOUBLE_TIME))

                    layout = Layout.from_name(self.bot, 'double')
                else:
                    await player.apply_powerup(Multiplier(3, time.time() + INDIV_TRIPLE_TIME))

                    for other in player.team.players:
                        if other != player:
                            await other.apply_powerup(Multiplier(3, time.time() + TEAM_TRIPLE_TIME))

                    layout = Layout.from_name(self.bot, 'triple')

                if layout is not None:
                    args = {
                        'eventnick': player.nick,
                        'teamname': player.team.name,
                    }                    
                    ls = LunaScript.from_layout(msg.channel, layout, args=args, member=player.member)
                    await ls.send()

    @commands.command()
    async def redeem(self, ctx):
        # for team in self.teams.values():
        #     if ctx.author == team.captain:
        #         break 
        # else:
        #     return 
        team = self.players[ctx.author.id].team
        
        if team.redeems == 0:
            return await ctx.send('You have no more powerups to redeem!')

        choices = random.sample(self.powerups_1k, 3)

        embed = discord.Embed(color=0xcab7ff, title='Redeem a Powerup') 
        for i, choice in enumerate(choices):
            embed.add_field(name=f'{i+1}', value=choice, inline=False)
         
        view = RedeemView(ctx, choices, self.powerups_1k)
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()

        if view.inter is None:
            await msg.delete()
            return

        query = 'update redeems set number = number - 1 where team = ?'
        await self.bot.db.execute(query, team.name)
        team.redeems -= 1
        query = 'insert into saved_powerups (team, option, time) values (?, ?, ?)'
        await self.bot.db.execute(query, team.name, int(view.custom_id), int(time.time()))

        choice = choices[int(view.custom_id) - 1][0]
        await view.inter.response.edit_message(content=f'**You have redeemed:**\n`{choice}`\n\nUse `!usepowerup` to use it anytime!', view=None)
    
    @commands.command()
    async def usepowerup(self, ctx):
        for team in self.teams.values():
            if ctx.author == team.captain:
                break
        else:
            return
        
        powerups = team.saved_powerups
        if len(powerups) == 0:
            return await ctx.send('You have no saved powerups!')
        
        embed = discord.Embed(color=0xcab7ff, title='Use a Powerup')
        for i, powerup_i in enumerate(powerups):
            embed.add_field(name=f'{i+1}', value=self.powerups[powerup_i], inline=False)
        embed.set_footer(text='Type the number to use the powerup')

        temp = await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            await temp.delete()
            return
        
        if not msg.content.isdigit() or int(msg.content) > len(powerups) or int(msg.content) < 1:
            await ctx.send('That is not a valid number!', ephemeral=True)
            return
        
        powerup = powerups[int(msg.content) - 1]
        team.powerups.remove(powerup)
        query = 'delete from saved_powerups where team = ? and option = ? limit 1'
        await self.bot.db.execute(query, team.name, powerup)

        if powerup == 0:
            n = await team.option1()
            await ctx.send(f'Your captain used a powerup that claimed **{n}** points for your team!')
        elif powerup == 1:
            n = await team.option2()
            await ctx.send(f'Your captain used a powerup that stole **{n}** points from the other team!')
        elif powerup == 2:
            await team.option3()
            await ctx.send('Your captain used a powerup that **doubled** all incoming points for __30 minutes__!')
        elif powerup == 3:
            await team.option4()
            await ctx.send('Your captain used a powerup that **tripled** all incoming points for __20 minutes__!')
        else:
            await team.option5()
            await ctx.send('Your captain used a powerup that **reduced the cooldown** for messages to __1 minute__ for __25 minutes__!')
    
    @commands.command()
    async def teampoints(self, ctx):
        embed = discord.Embed(title='Points for each team', color=0xcab7ff)
        for team in self.teams:
            embed.add_field(name=team, value=f'{self.teams[team].total_points:,}')
        await ctx.send(embed=embed)
    
    @commands.command()
    async def points(self, ctx):
        embed = discord.Embed(title='Points for each player', color=0xcab7ff)
        for team in self.teams:
            pointlst = []
            for player in self.teams[team].players:
                pointlst.append(f'**{player.nick}** - {player.points:,}')
            embed.add_field(name=team, value='\n'.join(pointlst))
        await ctx.send(embed=embed)
    
    @commands.command()
    async def pointslb(self, ctx):
        embed = discord.Embed(title='Points leaderboard', color=0xcab7ff)
        pointlst = []
        players = sorted(self.players.values(), key=lambda x: x.points, reverse=True)
        i = 1
        for player in players:
            pointlst.append(f'#{i}: **{player.nick}** - {player.points:,}')
            i += 1
        embed.description = '\n'.join(pointlst)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ServerEvent(bot))

