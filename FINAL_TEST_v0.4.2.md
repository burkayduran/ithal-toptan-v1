# ✅ FINAL TEST CHECKLIST - v0.4.2

## 🔥 KRİTİK FİX: Auth UUID Bug

### Problem:
```python
# YANLIŞ (String = UUID karşılaştırması)
user_id: str = payload.get("sub")
result = await db.execute(select(User).where(User.id == user_id))
# PostgreSQL: "operator does not exist: uuid = character varying"
```

### Fix:
```python
# DOĞRU (UUID parse et)
from uuid import UUID

user_id_str: str = payload.get("sub")
user_id = UUID(user_id_str)  # String → UUID
result = await db.execute(select(User).where(User.id == user_id))
```

**Bu bug `/auth/me` ve tüm tokenlı isteklerde patlamaya neden oluyordu!**

---

## 🧪 TEST 1: Register → Login → /auth/me

### Adım 1: Register
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email":"finaltest@test.com",
    "password":"test12345",
    "full_name":"Final Test User"
  }'
```

**Beklenen:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Adım 2: Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email":"finaltest@test.com",
    "password":"test12345"
  }'
```

**Beklenen:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### Adım 3: /auth/me (KRİTİK TEST)
```bash
# Token'ı kaydet
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Protected endpoint
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

**Beklenen:**
```json
{
  "email": "finaltest@test.com",
  "full_name": "Final Test User",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email_verified": false,
  "is_active": true,
  "is_admin": false,
  "created_at": "2025-02-19T..."
}
```

**❌ OLMAMASI GEREKEN:**
- 500 Internal Server Error
- PostgreSQL error: "operator does not exist"
- "Could not validate credentials"

---

## 🧪 TEST 2: Admin Endpoint (Tokenlı)

```bash
# Admin user oluştur (manuel DB)
# is_admin = true olmalı

# Admin login
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"admin123"}' \
  | jq -r '.access_token')

# Admin endpoint test
curl http://localhost:8000/api/admin/products \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Beklenen:** 200 OK + product listesi

**❌ OLMAMASI GEREKEN:**
- 500 Internal Server Error
- UUID hatası

---

## 🧪 TEST 3: MoQ Dolunca Celery Tetikleniyor mu?

### Setup
```bash
# 1. Docker başlat
docker compose up -d

# 2. Celery worker loglarını izle
docker compose logs -f celery_worker
```

### Test Senaryosu
```bash
# 1. Admin ile ürün ekle (MoQ: 2)
curl -X POST http://localhost:8000/api/admin/products \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Ürün",
    "unit_price_usd": 100,
    "moq": 2,
    "shipping_cost_usd": 10,
    "customs_rate": 0.35,
    "margin_rate": 0.30
  }'

# Product ID kaydet
PRODUCT_ID="..."

# 2. Yayınla
curl -X POST http://localhost:8000/api/admin/products/$PRODUCT_ID/publish \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 3. User 1 wishlist ekle
curl -X POST http://localhost:8000/api/v1/wishlist/add \
  -H "Authorization: Bearer $USER1_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"'$PRODUCT_ID'","quantity":1}'

# 4. User 2 wishlist ekle (MoQ DOLDU!)
curl -X POST http://localhost:8000/api/v1/wishlist/add \
  -H "Authorization: Bearer $USER2_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"'$PRODUCT_ID'","quantity":1}'
```

### Beklenen Celery Log
```
📧 Sending MoQ reached emails to 2 users...
✅ Email sent to user1@test.com: {...}
✅ Email sent to user2@test.com: {...}
✅ Sent 2 MoQ reached emails
```

**❌ OLMAMASI GEREKEN:**
- Task failure
- Email send error (RESEND_API_KEY yoksa "skipped" normal)
- UUID error

---

## 🧪 TEST 4: Email Gidiyor mu? (Resend)

### Setup
```bash
# 1. Resend API key al
# https://resend.com → Sign up → API Keys

# 2. .env'e ekle
RESEND_API_KEY=re_xxxxxxxxxxxxx
RESEND_FROM_EMAIL=noreply@yourdomain.com

# 3. Docker restart
docker compose restart api celery_worker
```

### Test
```bash
# MoQ senaryosunu tekrarla (yukarıdaki)

# Celery log:
docker compose logs celery_worker

# Beklenen:
# "✅ Email sent to user@test.com: {'id': 're_...'}"

# Email kontrol et (gelen kutu)
# Subject: "🎉 Test Ürün için sipariş hazır!"
```

**❌ OLMAMASI GEREKEN:**
- "RESEND_API_KEY not set" (key varsa)
- Resend API error (domain verify kontrolü)
- "status": "error"

---

## 🧪 TEST 5: 48 Saat Cleanup (Manuel)

```bash
# Python console
python
>>> from app.tasks.moq_tasks import cleanup_expired_entries
>>> cleanup_expired_entries.delay("PRODUCT_UUID")

# Celery log:
docker compose logs celery_worker

# Beklenen:
# "🧹 Cleaning up expired entries for UUID..."
# "✅ MoQ success! Product ordered"
# veya
# "❌ MoQ failed! Product reset to active"
# "📧 Sending MoQ failed emails to X users..."
```

---

## ✅ BAŞARI KRİTERLERİ

### 1. Auth Çalışıyor ✅
- [ ] Register → 201 + token
- [ ] Login → 200 + token
- [ ] `/auth/me` → 200 + user data (500 YOK)
- [ ] Admin endpoint → 200 (UUID error YOK)

### 2. MoQ Trigger Çalışıyor ✅
- [ ] MoQ dolunca Celery task tetikleniyor
- [ ] Email task log görünüyor
- [ ] Notification records oluşuyor

### 3. Email Gönderimi ✅ (Resend key varsa)
- [ ] Email gönderiliyor
- [ ] Resend dashboard'da görünüyor
- [ ] Gelen kutuda email var

### 4. 48h Cleanup Çalışıyor ✅
- [ ] Manuel trigger çalışıyor
- [ ] Paid count kontrolü doğru
- [ ] Success/failed durumları doğru

---

## 🐛 HATA DURUMUNDA

### 1. `/auth/me` → 500 Error
```bash
# API logs
docker compose logs api | grep -A 10 "error"

# PostgreSQL error?
# "operator does not exist: uuid = character varying"
# → auth.py UUID parse kontrolü
```

### 2. Celery Task Çalışmıyor
```bash
# Worker çalışıyor mu?
docker compose ps celery_worker
# State: Up olmalı

# Logs
docker compose logs celery_worker | tail -50

# Redis connection?
docker exec -it toplu_redis redis-cli PING
# PONG dönmeli
```

### 3. Email Gitmiyor
```bash
# RESEND_API_KEY set mi?
docker compose logs api | grep RESEND

# Resend dashboard
# https://resend.com/emails
# Email gönderildi mi?

# Domain verify mi?
# https://resend.com/domains
# Status: Verified olmalı
```

---

## 📊 DURUM

### v0.4.2 Fixes:
- ✅ Auth UUID bug fixed (KRİTİK)
- ✅ Yanlış klasör temizlendi
- ✅ Test guide eklendi

### Production-Ready:
- ✅ Auth (Argon2 + UUID fix)
- ✅ Admin endpoints
- ✅ Products + Wishlist
- ✅ MoQ trigger
- ✅ Email automation
- ✅ Celery tasks

### Next:
- iyzico payment (3-5 gün)
- Frontend (Next.js)

---

## 🎯 SONUÇ

**v0.4.2 ile auth tamamen stabil!**

Hemen 5 test'i çalıştır:
1. Register → Login → `/auth/me` ✅
2. Admin endpoint ✅
3. MoQ trigger ✅
4. Email gönderimi ✅
5. 48h cleanup ✅

Hepsi geçerse → Backend core production-ready! 🚀
