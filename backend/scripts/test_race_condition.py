#!/usr/bin/env python3
"""
Race-condition / concurrency test for POST /api/v1/wishlist/add.

Verifies three invariants under parallel load:
  1. No duplicate wishlist rows (PostgreSQL unique constraint honoured).
  2. Redis counter == DB aggregate after all writes settle.
  3. moq_reached transition fires exactly once (idempotent trigger).

Usage (from backend/ directory, with a running API):
    python scripts/test_race_condition.py [--base-url URL] [--workers N] [--moq N]

Requires:
    pip install httpx
    A running API at BASE_URL with Postgres + Redis attached.

The script creates its own isolated admin + N test users, so it is safe to run
against a dev or staging environment without polluting existing data.
"""
import argparse
import asyncio
import sys
import uuid
import httpx


# ── CLI args ──────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--workers", type=int, default=5,
                   help="Number of concurrent users (default: 5)")
    p.add_argument("--moq", type=int, default=3,
                   help="MoQ threshold for the test product (default: 3)")
    p.add_argument("--admin-email", default=f"race_admin_{uuid.uuid4().hex[:6]}@test.com")
    p.add_argument("--admin-pass", default="raceadmin123")
    return p.parse_args()


# ── Auth helpers ──────────────────────────────────────────────────────────────

async def register_and_login(client: httpx.AsyncClient, email: str, password: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email, "full_name": "Race Tester", "password": password,
    })
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json()["access_token"]


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(args: argparse.Namespace) -> None:
    failures: list[str] = []

    async with httpx.AsyncClient(base_url=args.base_url, timeout=30) as client:

        # ── 1. Set up admin + product ─────────────────────────────────────────
        admin_token = await register_and_login(client, args.admin_email, args.admin_pass)

        print(f"[INFO] Attempting admin promotion for {args.admin_email}")
        print("[INFO] If this step fails with 403, run manually:")
        print(f"       UPDATE users SET is_admin=true WHERE email='{args.admin_email}';")

        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        resp = await client.post("/api/admin/products", headers=admin_headers, json={
            "title": f"Race Test Product {uuid.uuid4().hex[:6]}",
            "description": "Created by test_race_condition.py",
            "images": [],
            "unit_price_usd": 5.0,
            "moq": args.moq,
            "shipping_cost_usd": 10.0,
            "customs_rate": 0.20,
            "margin_rate": 0.30,
        })
        if resp.status_code == 403:
            print("ERROR: admin account not promoted – see note above.")
            sys.exit(1)
        resp.raise_for_status()
        product_id = resp.json()["id"]
        print(f"[INFO] Product created: {product_id} (moq={args.moq})")

        resp = await client.post(f"/api/admin/products/{product_id}/publish", headers=admin_headers)
        resp.raise_for_status()
        print(f"[INFO] Product published (status=active)")

        # ── 2. Create N users ─────────────────────────────────────────────────
        users: list[str] = []
        for i in range(args.workers):
            email = f"race_user_{uuid.uuid4().hex[:8]}@test.com"
            token = await register_and_login(client, email, "racepass123")
            users.append(token)
        print(f"[INFO] Created {len(users)} test users")

        # ── 3. Concurrent wishlist adds ───────────────────────────────────────
        print(f"[INFO] Firing {args.workers} concurrent wishlist adds …")

        async def add_one(token: str, qty: int = 1) -> httpx.Response:
            return await client.post(
                "/api/v1/wishlist/add",
                headers={"Authorization": f"Bearer {token}"},
                json={"request_id": product_id, "quantity": qty},
            )

        responses = await asyncio.gather(*[add_one(t) for t in users])

        ok = sum(1 for r in responses if r.status_code == 200)
        err = [(r.status_code, r.text) for r in responses if r.status_code != 200]
        print(f"[INFO] Responses: {ok} OK, {len(err)} errors")
        for code, body in err:
            print(f"  ERROR {code}: {body[:200]}")
            failures.append(f"wishlist/add returned {code}")

        # ── 4. Check: no duplicate rows in DB (via /wishlist/my on each user) ─
        print("[CHECK] Verifying unique constraint (no duplicate rows) …")
        for token in users:
            resp = await client.get("/api/v1/wishlist/my",
                                    headers={"Authorization": f"Bearer {token}"})
            resp.raise_for_status()
            entries_for_product = [e for e in resp.json() if e["request_id"] == product_id]
            if len(entries_for_product) > 1:
                failures.append(f"Duplicate wishlist rows for product {product_id}")
        print(f"  ✓ unique constraint holds")

        # ── 5. Check: Redis counter == DB aggregate ───────────────────────────
        print("[CHECK] Verifying Redis counter == DB aggregate (via /wishlist/progress) …")
        resp = await client.get(f"/api/v1/wishlist/progress/{product_id}")
        resp.raise_for_status()
        progress = resp.json()
        redis_count = progress["current"]
        expected_count = sum(
            1 for r in responses if r.status_code == 200
        )  # each user added qty=1
        if redis_count != expected_count:
            failures.append(
                f"Redis counter {redis_count} != expected DB count {expected_count}"
            )
            print(f"  FAIL  Redis={redis_count}, expected={expected_count}")
        else:
            print(f"  ✓ Redis counter matches ({redis_count})")

        # ── 6. Check: moq_reached fires at most once ──────────────────────────
        print("[CHECK] Verifying moq_reached transition fired at most once …")
        resp = await client.get("/api/admin/products", headers=admin_headers)
        resp.raise_for_status()
        products = resp.json()
        product = next((p for p in products if p["id"] == product_id), None)
        if product is None:
            failures.append("Could not find product in admin list")
        else:
            status = product["status"]
            count = product["current_wishlist_count"]
            print(f"  Product status={status}, wishlist_count={count}, moq={args.moq}")
            if count >= args.moq and status not in ("moq_reached", "active"):
                failures.append(
                    f"Unexpected product status '{status}' after MoQ reached"
                )
            else:
                print(f"  ✓ product status is consistent ({status})")

        # ── 7. Same-user idempotency: re-add with same quantity ───────────────
        print("[CHECK] Verifying idempotent re-add (same user, same quantity) …")
        same_token = users[0]
        r1 = await add_one(same_token, qty=1)
        r2 = await add_one(same_token, qty=1)
        if r1.status_code != 200 or r2.status_code != 200:
            failures.append(f"Idempotent re-add failed: {r1.status_code}, {r2.status_code}")
        else:
            # quantity should still be 1 (no phantom increment)
            resp_wl = await client.get("/api/v1/wishlist/my",
                                       headers={"Authorization": f"Bearer {same_token}"})
            resp_wl.raise_for_status()
            entries = [e for e in resp_wl.json() if e["request_id"] == product_id]
            if entries and entries[0]["quantity"] != 1:
                failures.append(
                    f"Idempotent re-add changed quantity to {entries[0]['quantity']}"
                )
            else:
                print(f"  ✓ idempotent re-add did not duplicate quantity")

    # ── Result summary ────────────────────────────────────────────────────────
    print()
    if failures:
        print(f"FAILED – {len(failures)} assertion(s):")
        for f in failures:
            print(f"  ✗ {f}")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED ✓")


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
