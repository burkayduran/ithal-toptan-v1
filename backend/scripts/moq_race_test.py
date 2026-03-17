import asyncio, os, sys, httpx
API=os.getenv('API_BASE','http://localhost:8000')
TOKEN=os.getenv('TOKEN','')
REQUEST_ID=os.getenv('REQUEST_ID','')

async def hit():
    async with httpx.AsyncClient(timeout=20) as c:
        return await c.post(f"{API}/api/v1/wishlist/add",headers={"Authorization":f"Bearer {TOKEN}"},json={"request_id":REQUEST_ID,"quantity":1})

async def main():
    if not TOKEN or not REQUEST_ID:
        print('SKIP: TOKEN and REQUEST_ID env vars required', file=sys.stderr)
        sys.exit(0)
    rs=await asyncio.gather(*[hit() for _ in range(30)], return_exceptions=True)
    codes=[r.status_code for r in rs if hasattr(r,'status_code')]
    errors=[r for r in rs if isinstance(r, Exception)]
    print('codes',codes)
    if errors:
        print('errors', errors, file=sys.stderr)
        sys.exit(1)
    server_errors=[c for c in codes if c >= 500]
    if server_errors:
        print(f'FAIL: {len(server_errors)} 5xx responses', file=sys.stderr)
        sys.exit(1)
    print('OK: check logs/db: only one active->moq_reached transition should occur')

if __name__=='__main__':
    asyncio.run(main())
