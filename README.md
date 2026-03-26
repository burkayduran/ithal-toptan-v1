# Toplu Alışveriş Platformu

Grup alışveriş (group-buy) platformu — kullanıcılar kampanyalara katılır, MOQ dolunca ödeme süreci başlar.

---

## Mimari

```
frontend/   Next.js 14 (App Router) — kullanıcı ve admin arayüzü
backend/    FastAPI + SQLAlchemy (async) + PostgreSQL + Redis
```

---

## Hızlı Başlangıç

### Gereksinimler

- Docker & Docker Compose **veya** Python 3.12+ / Node.js 18+
- PostgreSQL 15+, Redis 7+

### Docker ile (Önerilen)

```bash
# 1. Env dosyasını hazırla
cp backend/.env.example backend/.env
# Gerekirse düzenle

# 2. Tüm servisleri başlat
docker compose up -d

# API:      http://localhost:8000
# API Docs: http://localhost:8000/api/docs
# Frontend: http://localhost:3000
```

### Local Dev (Docker olmadan)

```bash
# ── Backend ──────────────────────────────────────────────────────────────────
cd backend

# 1. Env dosyasını hazırla
cp .env.example .env
# DATABASE_URL ve REDIS_URL'i local değerlere göre düzenle

# 2. Virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Bağımlılıkları yükle
pip install -r requirements.txt
# Geliştirme araçları için (opsiyonel):
# pip install -r requirements-dev.txt

# 4. Database başlat (PostgreSQL çalışıyor olmalı)
createdb toplu_alisveris

# 5. API server
uvicorn app.main:app --reload --port 8000

# 6. Celery worker (ayrı terminal)
celery -A app.tasks.celery_app worker --loglevel=info

# 7. Celery beat — zamanlanmış görevler (ayrı terminal)
celery -A app.tasks.celery_app beat --loglevel=info

# ── Frontend ─────────────────────────────────────────────────────────────────
cd frontend

# 1. Env dosyasını hazırla
cp .env.local.example .env.local

# 2. Bağımlılıkları yükle
npm install

# 3. Dev server başlat
npm run dev        # http://localhost:3000
```

---

## API Endpoint Yapısı

### V2 Endpoints (Aktif — yeni domain modeli)

#### Public (auth gerektirmez)
```
GET    /api/v2/campaigns                     # Aktif kampanya listesi (paginated)
GET    /api/v2/campaigns/{id}               # Kampanya detayı
GET    /api/v2/campaigns/{id}/progress      # MOQ ilerleme (rate-limited)
GET    /api/v2/campaigns/{id}/similar       # Benzer kampanyalar
```

#### Kullanıcı (JWT gerekli)
```
GET    /api/v2/campaigns/my                 # Katıldığım kampanyalar
POST   /api/v2/campaigns/{id}/join          # Kampanyaya katıl
DELETE /api/v2/campaigns/{id}/leave         # Kampanyadan ayrıl
GET    /api/v2/payments/{participant_id}    # Ödeme/durum görünümü
POST   /api/v2/payments/{participant_id}/confirm  # Ödeme onayla
```

#### Admin (admin JWT gerekli)
```
POST   /api/v2/admin/campaigns              # Kampanya oluştur
GET    /api/v2/admin/campaigns              # Tüm kampanyalar (draft dahil)
GET    /api/v2/admin/campaigns/{id}         # Kampanya detayı (snapshot alanları dahil)
PATCH  /api/v2/admin/campaigns/{id}         # Güncelle / status değiştir
POST   /api/v2/admin/campaigns/{id}/publish # Draft → Active yayınla
POST   /api/v2/admin/campaigns/bulk-publish # Toplu yayınla
POST   /api/v2/admin/campaigns/bulk-cancel  # Toplu iptal
GET    /api/v2/admin/suggestions            # Kullanıcı önerileri
PATCH  /api/v2/admin/suggestions/{id}       # Öneri güncelle
GET    /api/v2/admin/categories             # Kategoriler
POST   /api/v2/admin/categories             # Kategori oluştur
PATCH  /api/v2/admin/categories/{id}        # Kategori güncelle
DELETE /api/v2/admin/categories/{id}        # Kategori sil
POST   /api/v2/admin/calculate-price        # Fiyat önizleme
```

### V1 Endpoints (Legacy)
```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
GET    /api/v1/auth/me
PATCH  /api/v1/auth/me
```

---

## Kampanya Status Akışı

```
draft → active → moq_reached → payment_collecting → ordered → shipped → delivered
  └──────────────────────────────────────────────────────────────┘
                          (herhangi bir aşamada cancelled)
```

- `draft` → `active`: Admin yayınlar
- `active` → `moq_reached`: MOQ dolunca (otomatik veya admin)
- `moq_reached`: Katılan kullanıcı `invited` statüsüne geçer, ödeme daveti gönderilir
- `payment_collecting` → `ordered`: Yeterli ödeme toplandı, sipariş verildi
- `ordered` → `shipped` → `delivered`: Kargo ve teslimat aşaması

### Payment Stage Eşlemesi (Frontend)

| participant_status | campaign_status | stage             |
|--------------------|-----------------|-------------------|
| joined / expired   | any             | campaign_active   |
| invited            | any             | moq_reached       |
| paid               | moq_reached / payment_collecting | payment_confirmed |
| paid               | ordered         | order_placed      |
| paid               | shipped         | shipping          |
| paid               | delivered       | delivered         |

---

## Backend Testleri

```bash
cd backend

# Syntax kontrolü
python -m compileall app/

# Import testi (env gerekli)
SECRET_KEY=test DATABASE_URL=postgresql+asyncpg://localhost/test \
  python -c "from app.main import app; print('OK')"

# Unit/integration testleri
pytest tests/ -v

# Belirli bir modül
pytest tests/test_campaigns.py -v
```

---

## Proje Yapısı

```
ithal-toptan-v1/
├── backend/
│   ├── .env.example            ← Env şablon dosyası
│   ├── requirements.txt
│   ├── requirements-dev.txt    ← Test/lint araçları
│   ├── alembic/                ← DB migrasyonları
│   └── app/
│       ├── main.py
│       ├── models/models.py    ← SQLAlchemy modelleri
│       ├── schemas/
│       │   ├── schemas.py      ← V1 schema (legacy)
│       │   └── v2_schemas.py   ← V2 schema (aktif)
│       ├── api/
│       │   ├── admin/admin_v2.py
│       │   └── v2/
│       │       ├── campaigns.py
│       │       └── payments.py
│       ├── services/
│       │   └── price_service.py
│       └── tasks/              ← Celery görevleri
├── frontend/
│   ├── .env.local.example      ← Env şablon dosyası
│   ├── app/                    ← Next.js App Router sayfaları
│   ├── components/campaign/    ← Kampanya bileşenleri
│   └── features/               ← Domain logic (hooks, API, types)
├── docker-compose.yml
└── README.md
```

---

## Sorun Giderme

### Port çakışması
```bash
docker compose down
sudo lsof -i :8000   # API portu
sudo lsof -i :5432   # PostgreSQL portu
```

### Database bağlantı hatası
`.env` dosyasında `DATABASE_URL` değerini kontrol et:
- Docker: `@db:5432`
- Local: `@localhost:5432`

### Migration hatası (dev only)
```bash
docker compose down -v
docker compose up -d
```
