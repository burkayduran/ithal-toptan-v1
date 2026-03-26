import asyncio, os, sys, httpx
API=os.getenv('API_BASE','http://localhost:8000')
TOKEN=os.getenv('TOKEN','')
REQUEST_ID=os.getenv('REQUEST_ID','')

async def hit(i):
    async with httpx.AsyncClient(timeout=20) as c:
        return await c.post(f"{API}/api/v1/wishlist/add",headers={"Authorization":f"Bearer {TOKEN}"},json={"request_id":REQUEST_ID,"quantity":2})

async def main():
    if not TOKEN or not REQUEST_ID:
        print('SKIP: TOKEN and REQUEST_ID env vars required', file=sys.stderr)
        sys.exit(0)
    rs=await asyncio.gather(*[hit(i) for i in range(20)], return_exceptions=True)
    codes=[r.status_code for r in rs if hasattr(r,'status_code')]
    print('status_codes',codes)
    if not all(c==200 for c in codes):
        print(f'FAIL: expected all 200, got {codes}', file=sys.stderr)
        sys.exit(1)
    print('OK parallel adds are 200')

if __name__=='__main__':
    asyncio.run(main())
