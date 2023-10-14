from discord.ext import commands 
import time 
import random 



class Leveling(commands.Cog):

    def __init__(self, bot):
        self.bot = bot 

        self.xp = {}  # a dictionary: user: xp

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return 
        
        if msg.guild is None:
            return
        
        increase = random.randint(5, 15)

        if msg.author in self.xp:
            self.xp[msg.author] += increase
        else:
            self.xp[msg.author] = increase

async def setup(bot):
    await bot.add_cog(Leveling(bot))
    
            
    
        