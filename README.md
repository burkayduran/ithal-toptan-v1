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

## 🚀 Hızlı Başlangıç

### Gereksinimler
- Docker & Docker Compose
- Python 3.12+ (local development için)

### Docker ile Çalıştırma (Önerilen)

```bash
# 1. Docker compose ile tüm servisleri başlat
docker compose up -d

# 2. API hazır!
# - API: http://localhost:8000
# - Docs: http://localhost:8000/api/docs
# - Health: http://localhost:8000/health

# Logları görüntüle
docker compose logs -f api

# Durdur
docker compose down
```

### Local Development (Docker olmadan)

```bash
# 1. PostgreSQL ve Redis yükle (macOS)
brew install postgresql redis

# 2. Servisleri başlat
brew services start postgresql
brew services start redis

# 3. Database oluştur
createdb toplu_alisveris

# 4. Virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 5. Dependencies yükle
pip install -r requirements.txt

# 6. .env dosyasını yapılandır
cp .env.example .env
# Düzenle:
# DATABASE_URL=postgresql+asyncpg://localhost/toplu_alisveris
# REDIS_URL=redis://localhost:6379/0
# RESEND_API_KEY=re_xxxxx (opsiyonel)

# 7. API server başlat
uvicorn app.main:app --reload --port 8000

# 8. Celery worker (ayrı terminal)
celery -A app.tasks.celery_app worker --loglevel=info

# 9. Celery beat (ayrı terminal)
celery -A app.tasks.celery_app beat --loglevel=info

# 10. Flower monitoring (opsiyonel, ayrı terminal)
celery -A app.tasks.celery_app flower --port=5555
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

## 🧪 Test

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
