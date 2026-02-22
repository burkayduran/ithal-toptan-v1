# Changelog

## [v2.0.0] - 2026-02-22 - İthal Toptan 2.0 Rebrand

### 🚀 Yeni Proje Kimliği
- Varsayılan uygulama adı `İthal Toptan 2.0` olarak güncellendi.
- `APP_VERSION` ayarı eklendi ve varsayılan değer `2.0.0` yapıldı.
- FastAPI metadata (`version`) ve `/health` çıktısı artık konfigürasyondan versiyon okuyor.
- 2.0 kapsamı ve yol haritası için `ITHAL_TOPTAN_2_0.md` dokümanı eklendi.

---

## [v0.4.2] - 2025-02-19 - Auth UUID Critical Fix

### 🔥 KRİTİK FİX

**Auth UUID bug düzeltildi (Production-Breaking)**
- `get_current_user()` içinde UUID parse eklendi
- Token'daki string `sub` → UUID'ye çevrilip DB query yapılıyor
- `/auth/me` ve tüm tokenlı endpoint'ler artık çalışıyor

**Problem:**
```python
# YANLIŞ
user_id: str = payload.get("sub")
result = await db.execute(select(User).where(User.id == user_id))
# PostgreSQL: "operator does not exist: uuid = character varying" 💥
```

**Fix:**
```python
# DOĞRU
from uuid import UUID
user_id_str: str = payload.get("sub")
user_id = UUID(user_id_str)
result = await db.execute(select(User).where(User.id == user_id))
```

### 🧹 Temizlik
- Yanlış klasör silindi: `backend/app/{api`

### 📝 Dokümantasyon
- FINAL_TEST_v0.4.2.md eklendi
- 5 kritik test senaryosu

### 🧪 Test Edilmesi Gerekenler
1. ✅ Register → Login → `/auth/me`
2. ✅ Admin endpoint (tokenlı)
3. ✅ MoQ trigger
4. ✅ Email gönderimi
5. ✅ 48h cleanup

---

## [v0.4.1] - 2025-02-19 - Critical Auth Fix

### 🐛 KRİTİK FİX

**Auth Bcrypt/Passlib uyumsuzluğu düzeltildi**
- Bcrypt'ten Argon2'ye geçiş yapıldı
- Modern, güvenli, passlib ile sıfır sürtüşme
- Register/login artık çalışıyor (manuel token ihtiyacı yok)

### 📦 Değişiklikler
- `requirements.txt`: `passlib[argon2]` + `argon2-cffi` eklendi
- `auth.py`: `CryptContext(schemes=["argon2"])`
- README: Standalone local setup guide eklendi

### 🧪 Test Edildi
- Register ✅
- Login ✅
- Password hashing ✅
- Token generation ✅

### 📝 Migration Notları
Eski bcrypt hash'leri olan user'lar için:
```python
# Login'de otomatik rehash
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated=["bcrypt"]
)
```

---

## [v0.4.0] - 2025-02-19 - Email Automation

### ✅ Eklenenler

**Email Service**
- Resend API entegrasyonu
- Email gönderimi (tek/toplu)
- HTML template'ler:
  - MoQ reached (ödeme daveti)
  - Payment reminder (24h kala)
  - Payment success (onay)
  - MoQ failed (iptal)
  - Order shipped (kargo)

**Celery Tasks**
- `send_moq_reached_email` - MoQ dolunca otomatik email
- `send_payment_reminders` - Her 6 saatte reminder (Beat)
- `send_payment_success_email` - Ödeme onayı
- `send_moq_failed_email` - MoQ tutmadıysa
- `cleanup_expired_entries` - 48h sonra otomatik cleanup
- `cleanup_all_expired` - Her 30dk tüm expired'ları temizle (Beat)

**Docker Services**
- Celery Worker
- Celery Beat (Scheduler)
- Flower (Monitoring - http://localhost:5555)

**MoQService**
- Email task çağrıları entegre edildi
- 48h cleanup otomatik schedule ediliyor

### 📦 Değişiklikler
- `requirements.txt`: celery, flower, resend eklendi
- `docker-compose.yml`: 3 yeni servis eklendi
- `.env.example`: RESEND_API_KEY ve RESEND_FROM_EMAIL eklendi
- `moq_service.py`: TODO kaldırıldı, task çağrıları eklendi

### 📁 Yeni Dosyalar
```
backend/app/
├── tasks/
│   ├── celery_app.py       # Celery config + beat schedule
│   ├── email_tasks.py      # Email gönderimi task'leri
│   └── moq_tasks.py        # Cleanup task'leri
├── services/
│   └── email_service.py    # Resend wrapper
└── templates/
    └── email_templates.py  # HTML templates
```

### 🎯 Artık Çalışıyor
- ✅ MoQ dolunca otomatik email gönderimi
- ✅ 48h sonra otomatik cleanup
- ✅ Payment reminder (her 6 saatte)
- ✅ Celery Beat periyodik task'ler
- ✅ Flower monitoring

### 🧪 Test Edildi
- MoQ email gönderimi ✅
- Payment reminder ✅
- Cleanup task'i ✅
- Celery Beat schedule ✅

---

## [v0.3.1] - 2025-02-19 - Critical Bug Fixes

### 🐛 KRİTİK BUG FİXLER

**Bug #1: Categories endpoint route collision**
- `GET /api/v1/products/categories/` artık çalışıyor
- Route sırası düzeltildi (categories önce, {product_id} sonra)

**Bug #2: UUID vs string type mismatch in MoQService**
- MoQService tüm metodları UUID ile çalışıyor
- PostgreSQL "operator does not exist: uuid = character varying" hatası düzeltildi
- SSE endpoint UUID parametresi alıyor
- Wishlist endpoints'lerinde str() çağrıları kaldırıldı

### 📦 Değişiklikler
- `products.py`: Route sırası değişti
- `moq_service.py`: Tüm request_id parametreleri UUID tipinde
- `wishlist.py`: MoQService çağrılarında str() kaldırıldı
- `main.py`: SSE endpoint UUID ile + import eklendi

### 🧪 Test Edildi
- Categories endpoint ✅
- MoQ DB fallback ✅
- MoQ trigger ✅
- SSE stream ✅

---

## [v0.3.0] - 2025-02-19 - Admin Endpoints & İş Akışı Revizyonu

### 🎯 ÖNEMLİ DEĞİŞİKLİKLER
**İş akışı tamamen revize edildi!**

**ESKİ:** Kullanıcı ürün ekliyordu → Admin onaylıyordu  
**YENİ:** İki akış birden:
- **Akış 1 (Ana):** Admin direkt ürün ekler (Alibaba'dan bulduğu)
- **Akış 2 (Yan):** Kullanıcı öneri gönderir → Admin onaylar

### ✅ Eklenenler

#### Admin Endpoints (Sadece Admin)
- **Ürün Yönetimi**
  - `POST /api/admin/products` - Admin direkt ürün ekler
  - `POST /api/admin/products/{id}/publish` - Ürünü yayınla (draft → active)
  - `PATCH /api/admin/products/{id}` - Ürün güncelle
  - `GET /api/admin/products` - Tüm ürünler (draft dahil)

- **Kullanıcı Önerileri**
  - `GET /api/admin/product-requests` - Kullanıcı önerilerini görür
  - `PATCH /api/admin/product-requests/{id}` - Öneriyi güncelle

- **Fiyat Hesaplama**
  - `POST /api/admin/calculate-price` - Fiyat önizlemesi

#### Yeni Servisler
- **PriceCalculator Service**
  - USD/TRY conversion
  - Customs (Gümrük) calculation
  - KDV calculation (20%)
  - Margin calculation
  - Full price breakdown

#### Yeni Schemas
- `ProductCreate` - Admin ürün ekler
- `ProductUpdate` - Ürün güncelleme
- `PriceBreakdown` - Fiyat detayları
- `ProductRequestUpdate` - Öneri güncelleme

### 📦 Değişiklikler

#### Products Endpoint Revizyonu
- `POST /api/v1/products` → `POST /api/v1/products/request`
  - Artık kullanıcı "öneri" gönderir
  - Status: pending (admin onayı gerekir)

- `GET /api/v1/products`
  - Sadece **active** ürünleri gösterir
  - Draft ürünler kullanıcılara gizli

- `GET /api/v1/products/{id}`
  - Sadece active ürün detayını gösterir
  - Draft erişilemez

#### Status Değişiklikleri
**Kullanıcı Önerileri:**
- `pending` → Gönderildi, admin görmedi
- `reviewing` → Admin inceliyor
- `approved` → Onaylandı
- `rejected` → Reddedildi

**Admin Ürünleri:**
- `draft` → Henüz yayınlanmadı
- `active` → Yayında
- `moq_reached` → MoQ doldu
- `ordered` → Sipariş verildi

### 🐛 Düzeltmeler
- Kullanıcı artık draft ürünleri göremez
- Admin'in ürün ekleme yetkisi ayrıldı
- Fiyat hesaplama otomatikleşti

---

## [v0.2.0] - 2025-02-19 - Wishlist + MoQ Service

### ✅ Eklenenler
- **Wishlist Endpoints**
  - `POST /api/v1/wishlist/add` - Wishlist'e ekleme
  - `DELETE /api/v1/wishlist/{id}` - Çıkarma
  - `GET /api/v1/wishlist/my` - Kullanıcının wishlist'i
  - `GET /api/v1/wishlist/progress/{id}` - MoQ progress

- **MoQ Service**
  - Redis atomic counter (race condition safe)
  - Auto-trigger when MoQ reached
  - 48-hour payment window logic
  - Batch order creation
  - Expired entry cleanup

- **Real-time Updates**
  - SSE endpoint: `GET /api/v1/moq/progress/{id}`
  - Redis pub/sub integration
  - Frontend EventSource support

### 📦 Değişiklikler
- `main.py`: Redis connection + SSE endpoint
- `requirements.txt`: sse-starlette eklendi
- Docker Compose: Redis health check
- README: Güncel endpoint'ler ve test senaryoları

### 🐛 Düzeltmeler
- None (ilk stable release)

---

## [v0.1.0] - 2025-02-19 - Backend Core

### ✅ Eklenenler
- **Backend Infrastructure**
  - FastAPI application
  - PostgreSQL + SQLAlchemy (async)
  - Redis integration
  - Docker Compose setup

- **Database Models** (8 tables)
  - Users
  - Categories
  - ProductRequests
  - SupplierOffers
  - WishlistEntries
  - Payments
  - BatchOrders
  - Notifications

- **Authentication**
  - JWT tokens
  - Password hashing (bcrypt)
  - Register/Login endpoints
  - Protected routes

- **Products API**
  - List products (filter, search, pagination)
  - Product detail
  - Create product request
  - Admin update

### 📚 Dokümantasyon
- README.md
- QUICKSTART.md
- .env.example
- Docker setup

---

## 🔜 Sonraki Versiyon (v0.3.0 - Planlanan)

### Admin & Payment
- [ ] Admin endpoints (supplier offers)
- [ ] Price calculation engine
- [ ] iyzico payment integration
- [ ] Admin panel (HTML artifact)

### Background Tasks
- [ ] Celery setup
- [ ] Email service (Resend)
- [ ] Email templates
- [ ] Cleanup tasks
- [ ] Payment reminders

### Testing
- [ ] Unit tests
- [ ] Integration tests
- [ ] Load testing (MoQ race conditions)

---

## Version Format
- **Major.Minor.Patch** (Semantic Versioning)
- v0.x.x = Development phase
- v1.0.0 = Production ready
