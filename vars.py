from discord.ext import commands


class Vars(commands.Cog):

    def __init__(self, bot):
        self.bot = bot 
        self.bot.vars = {}
    
    async def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator or ctx.author.id == self.bot.STORCH_ID 

    async def cog_load(self):
        query = 'SELECT name, value FROM vars'
        rows = await self.bot.db.fetch(query)
        for row in rows:
            if row[1].isdigit():
                row[1] = int(row[1])
            self.bot.vars[row[0]] = row[1]

    @commands.command()
    async def setvar(self, ctx, name: str, *, value: str):
        query = 'INSERT INTO vars(name, value) VALUES(?, ?) ON CONFLICT(name) DO UPDATE SET value = ?'
        await self.bot.db.execute(query, name, value, value)
        self.bot.vars[name] = value
        await ctx.send(f'Successfully set the variable `{name}` to `{value}`')
    
    @commands.command()
    async def getvar(self, ctx, name: str):
        value = self.bot.vars.get(name)
        if value is None:
            await ctx.send(f'No variable with the name `{name}` found')
            return 
        await ctx.send(value)
    
    @commands.command()
    async def delvar(self, ctx, name: str):
        query = 'DELETE FROM vars WHERE name = ?'
        await self.bot.db.execute(query, name)
        self.bot.vars.pop(name, None)
        await ctx.send(f'Successfully deleted the variable `{name}`')

async def setup(bot):
    await bot.add_cog(Vars(bot))


