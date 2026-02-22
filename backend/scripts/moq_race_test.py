import asyncio, os, httpx
API=os.getenv('API_BASE','http://localhost:8000')
TOKEN=os.getenv('TOKEN','')
REQUEST_ID=os.getenv('REQUEST_ID','')

async def hit():
    async with httpx.AsyncClient(timeout=20) as c:
        return await c.post(f"{API}/api/v1/wishlist/add",headers={"Authorization":f"Bearer {TOKEN}"},json={"request_id":REQUEST_ID,"quantity":1})

async def main():
    rs=await asyncio.gather(*[hit() for _ in range(30)], return_exceptions=True)
    codes=[r.status_code for r in rs if hasattr(r,'status_code')]
    print('codes',codes)
    print('check logs/db: only one active->moq_reached transition should occur')

if __name__=='__main__':
    asyncio.run(main())
