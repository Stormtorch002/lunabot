import asqlite


class DB:
    def __init__(self, bot):
        self.bot = bot 
        self.pool = None 

    async def connect(self):
        self.pool = await asqlite.create_pool('main.sqlite')

    async def execute(self, query, *args):
        async with self.pool.acquire() as conn:
            await conn.execute(query, args)
            await conn.commit()
    
    async def fetchrow(self, query, *args):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                return await cur.fetchone()
            
    async def fetch(self, query, *args):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                return await cur.fetchall()
            
    async def fetchval(self, query, *args):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                row = await cur.fetchone()
                if row is None:
                    return None 
                return row[0]



async def setup(bot):
    bot.db = DB(bot)
    await bot.db.connect()