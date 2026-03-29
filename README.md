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
# Gerekirse düzenle (özellikle RESEND_API_KEY ve SECRET_KEY)

# 2. Servisleri başlat (migration otomatik çalışır)
docker compose up --build -d

# API:      http://localhost:8000
# API Docs: http://localhost:8000/api/docs
# Frontend: http://localhost:3000 (ayrı adımla — aşağıya bakın)

# 3. Demo veri yükle (opsiyonel — kampanyaları doldurmak için)
docker compose exec api python scripts/seed.py

# 4. Admin kullanıcı oluştur
docker compose exec api python scripts/create_admin.py admin@example.com MySecret123
# Sonra: http://localhost:3000 → "Giriş Yap" → admin@example.com / MySecret123
# Admin panel: http://localhost:3000/admin
```

> **Not:** API container her başladığında `alembic upgrade head` çalışır, DB tabloları otomatik oluşur.

### Frontend (ayrı terminalde)

Frontend docker-compose'da yer almaz — yerel olarak çalıştırılır:

```bash
cd frontend
cp .env.local.example .env.local  # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev        # http://localhost:3000
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

# 4. DB oluştur ve migration çalıştır
createdb toplu_alisveris
alembic upgrade head

# 5. Demo veri (opsiyonel)
python scripts/seed.py

# 6. Admin kullanıcı oluştur
python scripts/create_admin.py admin@example.com MySecret123

# 7. API server
uvicorn app.main:app --reload --port 8000

# 8. Celery worker (ayrı terminal, e-posta görevleri için)
celery -A app.tasks.celery_app worker --loglevel=info

# ── Frontend ─────────────────────────────────────────────────────────────────
cd frontend
cp .env.local.example .env.local
npm install
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

# Syntax kontrolü (DB gerekmez)
python -m compileall app/

# Pure logic testleri — DB/Redis gerekmez, her ortamda çalışır
python -m pytest tests/test_smoke_pure.py -v --noconftest

# Integration testleri — PostgreSQL + Redis gerekir
# docker-compose.test.yml ile hafif test ortamı kaldır:
docker compose -f ../docker-compose.test.yml up -d
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/toplu_test \
  REDIS_URL=redis://localhost:6380/0 \
  python -m pytest tests/ -v
docker compose -f ../docker-compose.test.yml down -v
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

### Mevcut DB var, alembic versiyonu yok
Eğer tablolar elle oluşturulmuşsa ve alembic_version tablosu yoksa:
```bash
docker compose exec api alembic stamp head
docker compose restart api
```

### Admin panele giriş yapamıyorum
Admin kullanıcısını oluştur veya mevcut kullanıcıyı yükselt:
```bash
docker compose exec api python scripts/create_admin.py email@example.com YeniSifre123
```
Ardından frontend'den bu e-posta ve şifreyle giriş yap → `/admin` sayfasına git.
