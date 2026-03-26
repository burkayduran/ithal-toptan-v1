import asyncio, os
import redis.asyncio as aioredis

REDIS_URL=os.getenv('REDIS_URL','redis://localhost:6379/0')
KEY='moq:count:test-race'

LUA="""
local newVal = redis.call('INCRBY', KEYS[1], ARGV[1])
local ttl = redis.call('TTL', KEYS[1])
if ttl == -1 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
return newVal
"""

async def worker(r):
    await r.eval(LUA,1,KEY,1,30*24*3600)

async def main():
    r=aioredis.from_url(REDIS_URL, decode_responses=True)
    await r.delete(KEY)
    await asyncio.gather(*[worker(r) for _ in range(200)])
    val=int(await r.get(KEY) or 0)
    ttl=await r.ttl(KEY)
    print('val',val,'ttl',ttl)
    assert val==200
    assert ttl and ttl>0
    await r.aclose()

if __name__=='__main__':
    asyncio.run(main())
