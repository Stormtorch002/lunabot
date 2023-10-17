from db import DB 
import asyncio 


db = DB(None, 'test.sqlite')
# make a test table
async def setup():
    await db.connect()
    await db.execute('CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)')
    await db.execute('create table if not exists test2 (id INTEGER PRIMARY KEY, name TEXT)')
    for i in range(10):
        await db.execute('INSERT INTO test (name) VALUES (?)', f'test {i}')
        await db.execute('insert into test2 (name) values (?)', f'test2 {i}')
        await asyncio.sleep(1)

loop = asyncio.get_event_loop()
loop.run_until_complete(setup())

quit()
print('gg')
async def test():
    for i in range(10):
        await db.execute('INSERT INTO test (name) VALUES (?)', f'test {i}')
        await db.execute('insert into test2 (name) values (?)', f'test2 {i}')
        await asyncio.sleep(1)

asyncio.run(test())