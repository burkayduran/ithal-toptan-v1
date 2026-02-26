# Toplu Alışveriş Platformu - Backend Core

## ✅ Tamamlanan Özellikler

### Hafta 1 - Backend Core ✓
- ✅ FastAPI application
- ✅ PostgreSQL + SQLAlchemy (async)
- ✅ Redis integration + MoQ Service
- ✅ JWT Authentication
- ✅ 8 Database models
- ✅ Wishlist + Real-time SSE
- ✅ Docker Compose setup

### Hafta 2 - Admin Panel ⭐ YENİ
- ✅ Admin endpoints
- ✅ Price calculator
- ✅ Dual workflow (Admin ekler + User önerir)
- ✅ Draft/Publish system

### API Endpoints

#### 🔴 Admin Endpoints (Sadece Admin)
```
POST   /api/admin/products              # Direkt ürün ekle
POST   /api/admin/products/{id}/publish # Yayınla
PATCH  /api/admin/products/{id}         # Güncelle
GET    /api/admin/products              # Tüm ürünler (draft dahil)
GET    /api/admin/product-requests      # Kullanıcı önerileri
PATCH  /api/admin/product-requests/{id} # Öneri güncelle
POST   /api/admin/calculate-price       # Fiyat önizleme
```

#### 🟢 Authentication
- `POST /api/v1/auth/register` - Yeni kullanıcı kaydı
- `POST /api/v1/auth/login` - Giriş
- `GET /api/v1/auth/me` - Mevcut kullanıcı bilgisi
- `PATCH /api/v1/auth/me` - Profil güncelleme

#### 🟢 Products (Public)
```
GET    /api/v1/products                 # Aktif ürünler (yayınlanmış)
GET    /api/v1/products/{id}            # Ürün detayı
POST   /api/v1/products/request         # Ürün önerisi gönder
GET    /api/v1/products/categories/     # Kategoriler
```

#### 🟢 Wishlist ⭐
- `POST /api/v1/wishlist/add` - Wishlist'e ekle
- `DELETE /api/v1/wishlist/{id}` - Çıkar
- `GET /api/v1/wishlist/my` - Tüm wishlist'im
- `GET /api/v1/wishlist/progress/{id}` - MoQ progress

#### Real-time Updates ⭐ YENİ
- `GET /api/v1/moq/progress/{id}` - SSE stream (real-time MoQ updates)

### MoQ Service ⭐ YENİ
- ✅ Redis atomic counter (race condition safe)
- ✅ Auto-trigger when MoQ reached
- ✅ 48-hour payment window
- ✅ Expired entry cleanup
- ✅ Batch order creation
- ✅ Real-time pub/sub for SSE

---

## 🚀 Quick Start (Mac / Linux)

### Prerequisites
- Docker & Docker Compose **or** Python 3.12+ with Postgres 16 + Redis 7

### Option A – Docker (recommended, zero config)

```bash
# Clone and start all services (API, Celery, Postgres, Redis, Flower)
git clone <repo-url>
cd ithal-toptan-v1

# Copy environment template
cp backend/.env.example backend/.env   # edit SECRET_KEY at minimum

# Start everything
docker compose up -d

# Verify
curl http://localhost:8000/health
# → {"status":"ok","app":"İthal Toptan 2.0","version":"2.0.0"}

# Interactive API docs
open http://localhost:8000/api/docs

# Logs
docker compose logs -f api

# Stop
docker compose down
```

### Option B – Local Python (Mac / Linux)

```bash
# 1. Install dependencies (macOS with Homebrew)
brew install postgresql@16 redis python@3.12

# Linux (Debian/Ubuntu)
sudo apt-get install -y postgresql redis-server python3.12

# 2. Start Postgres + Redis
brew services start postgresql@16   # macOS
brew services start redis
# or: pg_ctl start / redis-server --daemonize yes (Linux)

# 3. Create the database
createdb toplu_alisveris

# 4. Python virtual environment
cd backend
python3.12 -m venv venv
source venv/bin/activate

# 5. Install Python dependencies (includes pytest + alembic)
pip install -r requirements.txt

# 6. Create .env
cat > .env <<'EOF'
SECRET_KEY=change-me-to-random-string
DATABASE_URL=postgresql+asyncpg://localhost/toplu_alisveris
REDIS_URL=redis://localhost:6379/0
EMAIL_PROVIDER=fake
MOQ_SYNC_STRATEGY=lazy
EOF

# 7. (Optional) Run Alembic migrations instead of auto-create
alembic upgrade head

# 8. Start the API (auto-creates tables if not using Alembic)
uvicorn app.main:app --reload --port 8000

# 9. Celery worker (separate terminal, same venv)
celery -A app.tasks.celery_app worker --loglevel=info

# 10. Celery beat scheduler (separate terminal)
celery -A app.tasks.celery_app beat --loglevel=info

# 11. Flower monitoring UI (optional, separate terminal)
celery -A app.tasks.celery_app flower --port=5555
# open http://localhost:5555
```

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | ✅ | – | JWT signing secret |
| `DATABASE_URL` | ✅ | – | `postgresql+asyncpg://...` |
| `REDIS_URL` | ✅ | – | `redis://host:port/db` |
| `EMAIL_PROVIDER` | | `resend` | `resend` or `fake` |
| `RESEND_API_KEY` | | – | Required if `EMAIL_PROVIDER=resend` |
| `MOQ_SYNC_STRATEGY` | | `lazy` | `strict` (sync every write) or `lazy` (sync on cache miss) |
| `FRONTEND_URL` | | `http://localhost:3000` | CORS allowed origin |

### Seed data for wishlist testing

```bash
# Create admin + product + publish + wishlist entry automatically
cd backend
python scripts/seed_test_data.py

# Or print the equivalent curl sequence
python scripts/seed_test_data.py --curl

# Promote admin manually (required before seeding):
# docker exec -it toplu_db psql -U postgres toplu_alisveris \
#   -c "UPDATE users SET is_admin=true WHERE email='admin@test.com';"
```

---

## 📊 Veritabanı

Tables automatically created on startup:
- users
- categories
- product_requests
- supplier_offers
- wishlist_entries
- payments
- batch_orders
- notifications

## 🔑 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Yeni kullanıcı kaydı
- `POST /api/v1/auth/login` - Giriş
- `GET /api/v1/auth/me` - Mevcut kullanıcı bilgisi
- `PATCH /api/v1/auth/me` - Profil güncelleme

### Products
- `GET /api/v1/products` - Ürün listesi (filter, search, pagination)
- `GET /api/v1/products/{id}` - Ürün detayı
- `POST /api/v1/products` - Yeni ürün talebi (auth required)
- `PATCH /api/v1/products/{id}` - Ürün güncelle (admin)
- `GET /api/v1/products/categories/` - Kategoriler

## 🧪 Test Senaryoları

### 1. Authentication
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","full_name":"Test User"}'

# Response: {"access_token":"eyJ...","token_type":"bearer"}

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Save token
TOKEN="eyJ..."
```

### 2. Admin: Ürün Ekle ⭐ YENİ
```bash
# Admin login (önce admin user oluştur)
ADMIN_TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"admin123"}' | jq -r '.access_token')

# Fiyat önizleme
curl -X POST http://localhost:8000/api/admin/calculate-price \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "unit_price_usd": 800,
    "moq": 50,
    "shipping_cost_usd": 200,
    "customs_rate": 0.35,
    "margin_rate": 0.30
  }'

# Ürün ekle
PRODUCT_ID=$(curl -X POST http://localhost:8000/api/admin/products \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "iPhone 15 Pro Max 256GB",
    "description": "Apple iPhone 15 Pro Max",
    "unit_price_usd": 800,
    "moq": 50,
    "lead_time_days": 30,
    "shipping_cost_usd": 200,
    "customs_rate": 0.35,
    "margin_rate": 0.30
  }' | jq -r '.id')

# Yayınla
curl -X POST http://localhost:8000/api/admin/products/$PRODUCT_ID/publish \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 3. User: Ürün Önerisi ⭐ YENİ
```bash
# Kullanıcı ürün önerisi gönderir
curl -X POST http://localhost:8000/api/v1/products/request \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Samsung S24 Ultra",
    "description": "512GB version",
    "expected_price_try": 45000
  }'

# Admin önerileri görür
curl http://localhost:8000/api/admin/product-requests?status=pending \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 4. Products (Public)
```bash
# Aktif ürünleri listele (artık sadece yayınlanmış ürünler)
curl http://localhost:8000/api/v1/products

# Ürün detayı
curl http://localhost:8000/api/v1/products/$PRODUCT_ID
```

### 5. Wishlist
```bash
# Add to wishlist
curl -X POST http://localhost:8000/api/v1/wishlist/add \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"PRODUCT_UUID","quantity":1}'

# Get my wishlist
curl http://localhost:8000/api/v1/wishlist/my \
  -H "Authorization: Bearer $TOKEN"

# Get MoQ progress
curl http://localhost:8000/api/v1/wishlist/progress/PRODUCT_UUID

# Remove from wishlist
curl -X DELETE http://localhost:8000/api/v1/wishlist/PRODUCT_UUID \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Real-time MoQ Updates (SSE) ⭐ NEW
```javascript
// Frontend JavaScript
const eventSource = new EventSource('http://localhost:8000/api/v1/moq/progress/PRODUCT_UUID');

eventSource.onmessage = (event) => {
  const count = event.data;
  console.log('Current MoQ count:', count);
  // Update progress bar UI
  updateProgressBar(count);
};

eventSource.onerror = (error) => {
  console.error('SSE connection error:', error);
  eventSource.close();
};
```

### 5. Health Check
```bash
curl http://localhost:8000/health
# Response: {"status":"ok","app":"Toplu Alışveriş Platformu","version":"1.0.0"}
```

---

## 🎯 İş Akışı

### Wishlist → MoQ → Payment Flow

```
1️⃣ User adds to wishlist
   └─> Redis counter increments (atomic)
   
2️⃣ Counter >= MoQ threshold?
   ├─> YES: Trigger payment phase
   │   ├─> All "waiting" → "notified"
   │   ├─> Set 48h deadline
   │   └─> Create notification records
   └─> NO: Continue collecting

3️⃣ After 48 hours (Celery cleanup task)
   ├─> Mark expired entries
   ├─> Count paid entries
   └─> paid_count >= MoQ?
       ├─> YES: Create batch order
       └─> NO: Reset to "active"
```

---

## 🧪 Running Tests

### Integration tests (requires live Postgres + Redis)

```bash
cd backend

# Set required env vars (or create a .env.test file)
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test_ithal
export REDIS_URL=redis://localhost:6379/1
export SECRET_KEY=test-secret-key

# Create test database
createdb test_ithal  # or: psql -c "CREATE DATABASE test_ithal;"

# Install test dependencies (already in requirements.txt)
pip install -r requirements.txt

# Verify syntax
python -m compileall app

# Run all integration tests
pytest -q

# Run a specific test
pytest -q tests/test_integration.py::test_auth_register_login_me -v
```

### Tests included

| # | Test | Description |
|---|---|---|
| 1 | `test_auth_register_login_me` | Register → login → GET /me |
| 2 | `test_admin_create_and_publish_product` | Admin creates product + publishes to `active` |
| 3 | `test_wishlist_add_returns_200_and_correct_response` | Wishlist add returns 200 + correct `WishlistResponse` |
| 4 | `test_wishlist_add_rejected_for_draft_product` | Draft product returns 400 with `{error: "product_not_open", ...}` |
| 5 | `test_moq_threshold_transition_is_atomic` | Concurrent adds – only one MoQ transition fires |
| 6 | `test_sse_returns_503_when_redis_unavailable` | SSE returns 503 when `app.state.redis` is None |
| 7 | `test_sse_connects_and_receives_initial_message` | SSE streams initial count event |
| 8  | `test_raw_sql_insert_respects_server_defaults` | Raw SQL insert: `product_requests` / `supplier_offers` server_defaults |
| 8b | `test_raw_sql_insert_user_category_wishlist_defaults` | Raw SQL insert: `users` / `categories` / `wishlist_entries` server_defaults (migration 0003) |
| 9  | `test_same_user_concurrent_upsert` | Same user, N concurrent adds with different qtys → 1 DB row, Redis == DB qty |

### CI – GitHub Actions

Tests run automatically on every push/PR via `.github/workflows/tests.yml`
using Postgres 16 + Redis 7 service containers.

---

## 🔬 Smoke Tests & Race-Condition Tests

### Alembic migration smoke test

Verifies that `alembic upgrade head` succeeds on a clean database **and** that
all `server_default` values are correct (raw SQL inserts, no ORM).

```bash
cd backend

# Requires: psql + createdb + alembic in $PATH, Postgres running locally
bash scripts/alembic_smoke_test.sh

# Optional overrides:
PGHOST=localhost PGPORT=5432 PGUSER=postgres PGPASSWORD=postgres \
  bash scripts/alembic_smoke_test.sh
```

What it checks:
- `createdb` → `alembic upgrade head` exits 0
- `ALGORITHM=HS256` in the environment is silently accepted (demonstrates `extra="ignore"` fix)
- `product_requests`: `status='pending'`, `view_count=0`, `images='{}'` (raw SQL insert)
- `supplier_offers`: `supplier_country='CN'`, `margin_rate=0.25`, `is_selected=false`
- `alembic_version` table contains `0001` or `0002`
- Test database is dropped on exit (trap cleanup)

### Race-condition / concurrency test

Requires a **running API** (not in-process). Fires parallel wishlist adds and
verifies Redis integrity + PostgreSQL unique constraint.

```bash
cd backend
pip install httpx    # already in requirements.txt

# Start the API first:
uvicorn app.main:app --port 8000 &

python scripts/test_race_condition.py
# Optional flags:
python scripts/test_race_condition.py --workers 10 --moq 5 --base-url http://localhost:8000
```

Checks performed:
1. Multi-user concurrent adds → all return 200
2. Unique constraint: no duplicate `(user_id, request_id)` rows
3. Redis counter == DB aggregate after writes settle
4. `moq_reached` transition fires at most once (idempotent)
5. Idempotent same-user re-add (same quantity) doesn't phantom-increment
6. **Same-user concurrent UPSERT** (5 concurrent adds with quantities 1–5):
   - Exactly 1 DB row (PostgreSQL `ON CONFLICT DO UPDATE`)
   - Final quantity is one of the submitted values (last writer wins)
   - Redis counter == final DB quantity

## 📝 Tamamlanan ve Kalan İşler

### ✅ Hafta 1 - TAMAMLANDI
- [x] Backend core setup
- [x] Database models (8 tables)
- [x] Authentication (JWT)
- [x] Products CRUD
- [x] Wishlist endpoints
- [x] MoQ service (Redis counter)
- [x] MoQ trigger logic
- [x] SSE endpoint (real-time progress)
- [x] Docker Compose

### 🔄 Hafta 2 - SONRAKİ ADIMLAR
- [ ] Admin endpoints (supplier offers)
- [ ] Price calculation engine
- [ ] iyzico payment integration
- [ ] Celery tasks setup
- [ ] Email service (Resend)
- [ ] Email templates
- [ ] Background tasks (cleanup, reminders)

### 📅 Hafta 3 - FRONTEND
- [ ] Next.js setup
- [ ] Authentication pages
- [ ] Product listing & detail
- [ ] Wishlist UI
- [ ] Payment flow
- [ ] Real-time MoQ progress bar

---

## 🗂️ Proje Yapısı

```
toplu-alisveris/
├── docker-compose.yml          # PostgreSQL + Redis + API
├── README.md                   # Bu dosya
├── .gitignore
└── backend/
    ├── Dockerfile
    ├── requirements.txt        # Python dependencies
    ├── .env                    # Environment variables
    └── app/
        ├── main.py             # FastAPI application
        ├── core/
        │   ├── config.py       # Settings
        │   └── auth.py         # JWT utilities
        ├── db/
        │   └── session.py      # Database session
        ├── models/
        │   └── models.py       # SQLAlchemy models (8 tables)
        ├── schemas/
        │   └── schemas.py      # Pydantic schemas
        ├── services/
        │   └── moq_service.py  # MoQ tracking & trigger logic
        └── api/v1/endpoints/
            ├── auth.py         # Authentication endpoints
            ├── products.py     # Products endpoints
            └── wishlist.py     # Wishlist endpoints
```

---

## 📝 Sonraki Adımlar

## 🐛 Sorun Giderme

### Port zaten kullanımda
```bash
# PostgreSQL port conflict
docker compose down
sudo lsof -i :5432
# Process'i kill et

# API port conflict
sudo lsof -i :8000
```

### Database connection error
```bash
# .env dosyasında DATABASE_URL kontrol et
# Docker kullanıyorsan: @db:5432
# Local kullanıyorsan: @localhost:5432
```

### Migration errors
```bash
# Tabloları sıfırla (DEV ONLY!)
docker compose down -v
docker compose up -d
```

## 📞 İletişim

Hata bulursan veya soru varsa, lütfen detaylı açıklama ile bildir:
- Stack trace
- Request/response body
- Environment (Docker/local)
