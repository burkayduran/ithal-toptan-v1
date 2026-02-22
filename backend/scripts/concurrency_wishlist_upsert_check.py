"""Concurrent smoke test for wishlist UPSERT behavior.
Run API locally first, then:
  python backend/scripts/concurrency_wishlist_upsert_check.py
"""
import asyncio
import os
import uuid
import httpx

API = os.getenv("API_BASE", "http://localhost:8000")
TOKEN = os.getenv("TOKEN", "")
REQUEST_ID = os.getenv("REQUEST_ID", str(uuid.uuid4()))


async def hit(i: int):
    async with httpx.AsyncClient(timeout=15) as client:
        return await client.post(
            f"{API}/api/v1/wishlist/add",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={"request_id": REQUEST_ID, "quantity": 1 + (i % 3)},
        )


async def main():
    jobs = [hit(i) for i in range(20)]
    results = await asyncio.gather(*jobs, return_exceptions=True)
    ok = sum(1 for r in results if isinstance(r, httpx.Response) and r.status_code < 500)
    print(f"Completed {len(results)} requests, non-5xx={ok}")
    for r in results:
        if isinstance(r, Exception):
            print("ERR", r)
        else:
            print(r.status_code, r.text[:120])


if __name__ == "__main__":
    asyncio.run(main())
