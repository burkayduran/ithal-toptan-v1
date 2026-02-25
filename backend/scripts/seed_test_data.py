#!/usr/bin/env python3
"""
Seed script: create a product + selected offer + publish to 'active'.

Usage (from backend/ directory):
    python scripts/seed_test_data.py

Or via curl sequence (documented below).

Requires:
    BASE_URL  - API base URL          (default: http://localhost:8000)
    ADMIN_EMAIL / ADMIN_PASS          (default: admin@test.com / adminpass)

Environment variables can be set inline:
    BASE_URL=http://localhost:8000 python scripts/seed_test_data.py
"""
import asyncio
import json
import os
import sys
import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@test.com")
ADMIN_PASS = os.getenv("ADMIN_PASS", "adminpass123")
USER_EMAIL = os.getenv("USER_EMAIL", "wishtest@test.com")
USER_PASS = os.getenv("USER_PASS", "userpass123")


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # ── 1. Register admin (idempotent) ──────────────────────────────────
        resp = await client.post("/api/v1/auth/register", json={
            "email": ADMIN_EMAIL,
            "full_name": "Seed Admin",
            "password": ADMIN_PASS,
        })
        if resp.status_code not in (201, 400):
            resp.raise_for_status()

        # ── 2. Login admin ───────────────────────────────────────────────────
        resp = await client.post("/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASS,
        })
        resp.raise_for_status()
        admin_token = resp.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # ── 3. Promote admin to is_admin=True via direct DB (skip if already) ─
        #   (This step is done via DB directly; seed promotes via a known trick.
        #    In production, set is_admin=True in DB manually or via a migration.)
        print("NOTE: Ensure the admin account has is_admin=True in the database.")
        print("      You can run:  UPDATE users SET is_admin=true WHERE email='{}';".format(ADMIN_EMAIL))
        print("      Continuing with current token (will fail if not admin)...")

        # ── 4. Create product ────────────────────────────────────────────────
        resp = await client.post("/api/admin/products", headers=admin_headers, json={
            "title": "Seed Test Product",
            "description": "Created by seed_test_data.py",
            "images": ["https://placehold.co/400x400.png"],
            "unit_price_usd": 5.00,
            "moq": 3,
            "shipping_cost_usd": 50,
            "customs_rate": 0.20,
            "margin_rate": 0.30,
        })
        if resp.status_code == 403:
            print("ERROR: Admin account is not flagged as is_admin=True in the DB.")
            print("       Run: UPDATE users SET is_admin=true WHERE email='{}';".format(ADMIN_EMAIL))
            sys.exit(1)
        resp.raise_for_status()
        product = resp.json()
        product_id = product["id"]
        print(f"✓ Product created: {product_id}  (status={product['status']})")

        # ── 5. Publish product (draft → active) ──────────────────────────────
        resp = await client.post(f"/api/admin/products/{product_id}/publish", headers=admin_headers)
        resp.raise_for_status()
        print(f"✓ Product published: {resp.json()}")

        # ── 6. Register regular user (idempotent) ────────────────────────────
        resp = await client.post("/api/v1/auth/register", json={
            "email": USER_EMAIL,
            "full_name": "Wish Tester",
            "password": USER_PASS,
        })
        if resp.status_code not in (201, 400):
            resp.raise_for_status()

        # ── 7. Login regular user ────────────────────────────────────────────
        resp = await client.post("/api/v1/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASS,
        })
        resp.raise_for_status()
        user_token = resp.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # ── 8. Add product to wishlist ───────────────────────────────────────
        resp = await client.post("/api/v1/wishlist/add", headers=user_headers, json={
            "request_id": product_id,
            "quantity": 1,
        })
        resp.raise_for_status()
        wl = resp.json()
        print(f"✓ Wishlist entry created: id={wl['id']} status={wl['status']}")

        print("\n=== Seed complete ===")
        print(f"  Product ID  : {product_id}")
        print(f"  Admin token : {admin_token[:40]}...")
        print(f"  User token  : {user_token[:40]}...")
        print(f"\nRun wishlist tests against product_id={product_id}")


# ── Documented curl sequence ──────────────────────────────────────────────────
CURL_SEQUENCE = """
# 1. Register admin
curl -s -X POST http://localhost:8000/api/v1/auth/register \\
  -H 'Content-Type: application/json' \\
  -d '{"email":"admin@test.com","password":"adminpass123","full_name":"Admin"}' | jq .

# 2. Promote to admin (run in psql or docker exec):
#    UPDATE users SET is_admin=true WHERE email='admin@test.com';

# 3. Login admin
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \\
  -H 'Content-Type: application/json' \\
  -d '{"email":"admin@test.com","password":"adminpass123"}' | jq -r .access_token)

# 4. Create product
PRODUCT_ID=$(curl -s -X POST http://localhost:8000/api/admin/products \\
  -H "Authorization: Bearer $ADMIN_TOKEN" \\
  -H 'Content-Type: application/json' \\
  -d '{"title":"Test Product","unit_price_usd":5,"moq":3,"shipping_cost_usd":50,"customs_rate":0.20,"margin_rate":0.30}' | jq -r .id)
echo "Product: $PRODUCT_ID"

# 5. Publish product
curl -s -X POST "http://localhost:8000/api/admin/products/$PRODUCT_ID/publish" \\
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .

# 6. Register user
curl -s -X POST http://localhost:8000/api/v1/auth/register \\
  -H 'Content-Type: application/json' \\
  -d '{"email":"user@test.com","password":"userpass123","full_name":"User"}' | jq .

# 7. Login user
USER_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \\
  -H 'Content-Type: application/json' \\
  -d '{"email":"user@test.com","password":"userpass123"}' | jq -r .access_token)

# 8. Add to wishlist
curl -s -X POST http://localhost:8000/api/v1/wishlist/add \\
  -H "Authorization: Bearer $USER_TOKEN" \\
  -H 'Content-Type: application/json' \\
  -d "{\\\"request_id\\\":\\\"$PRODUCT_ID\\\",\\\"quantity\\\":1}" | jq .
"""

if __name__ == "__main__":
    if "--curl" in sys.argv:
        print(CURL_SEQUENCE)
        sys.exit(0)
    asyncio.run(main())
