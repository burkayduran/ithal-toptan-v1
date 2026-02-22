# v0.3.0 - Admin Endpoints & Revize Edilmiş Sistem

## 🎯 ÖNEMLİ DEĞİŞİKLİKLER

### İş Akışı Revizyonu

**ESKİ (Yanlış):**
- ❌ Kullanıcı ürün ekleyebiliyordu
- ❌ Admin sadece onaylıyordu

**YENİ (Doğru):**
- ✅ **İKİ AKIŞ BİRDEN**

### 🔵 AKIŞ 1: Admin Direkt Ürün Ekler (Ana İş)

```
Admin (Sen):
1. Alibaba'da iPhone 15 bulursun
2. Tedarikçi ile görüşürsün (MoQ, fiyat)
3. Admin panel → "Yeni Ürün Ekle"
4. Tüm bilgileri tek formda girersin:
   ├─ Ürün adı, açıklama, görseller
   ├─ Tedarikçi bilgileri
   ├─ Birim fiyat (USD), MoQ, lead time
   ├─ Kargo (USD), Gümrük oranı (%)
   └─ Marj oranı (%)
5. Sistem otomatik fiyat hesaplar → ₺42,450
6. "Taslak Olarak Kaydet" → Status: draft
7. Kontrol edersin
8. "Yayınla" → Status: active
9. Kullanıcılar artık görebilir ve wishlist'e ekleyebilir
```

### 🔵 AKIŞ 2: Kullanıcı Ürün Önerir (Yan İş)

```
Kullanıcı:
1. "Ürün Öner" butonuna tıklar
2. Form doldurur:
   ├─ Ürün adı: "Samsung S24 Ultra"
   ├─ Açıklama
   ├─ Link (opsiyonel)
   └─ Beklenen fiyat
3. Gönder → Status: pending

Admin (Sen):
1. Admin panel → "Öneriler" sekmesi
2. Pending önerileri görürsün
3. Beğenirsen:
   ├─ "İncele" → Status: reviewing
   ├─ Alibaba'da bulursun
   ├─ Teklif bilgilerini girersin
   └─ "Onayla & Yayınla" → Status: active
4. Kullanıcıya bildirim gider: "Öneriniz onaylandı!"
```

---

## 🆕 YENİ API ENDPOINTS

### 🔴 Admin Endpoints (Sadece Admin)

#### Ürün Yönetimi
```http
POST   /api/admin/products
# Admin direkt ürün ekler (teklif bilgileri dahil)
# Body: ProductCreate (title, description, unit_price_usd, moq, vs.)
# Response: ProductResponse

POST   /api/admin/products/{id}/publish
# Ürünü yayınla: draft → active
# Response: {message, id}

PATCH  /api/admin/products/{id}
# Ürünü güncelle
# Body: ProductUpdate
# Response: ProductResponse

GET    /api/admin/products
# Admin tüm ürünleri görür (draft dahil)
# Response: List[ProductResponse]
```

#### Kullanıcı Önerileri
```http
GET    /api/admin/product-requests?status=pending
# Kullanıcı önerilerini görür
# Response: List[ProductRequestResponse]

PATCH  /api/admin/product-requests/{id}
# Öneriyi güncelle (pending → reviewing → approved/rejected)
# Body: ProductRequestUpdate (status, admin_notes)
# Response: ProductRequestResponse
```

#### Fiyat Hesaplama
```http
POST   /api/admin/calculate-price
# Fiyat önizlemesi (teklif girmeden önce)
# Body: SupplierOfferCreate
# Response: PriceBreakdown
#   ├─ unit_price_try
#   ├─ shipping_per_unit_try
#   ├─ customs_try
#   ├─ kdv_try
#   ├─ total_cost_try
#   ├─ margin_try
#   └─ selling_price_try
```

---

### 🟢 User Endpoints (Revize Edildi)

```http
POST   /api/v1/products/request
# Kullanıcı ürün önerisi gönderir
# Body: ProductRequestCreate
# Response: {id, message}

GET    /api/v1/products
# Sadece ACTIVE ürünleri görür (draft görmez)
# Response: List[ProductResponse]

GET    /api/v1/products/{id}
# Sadece active ürün detayını görür
# Response: ProductResponse
```

---

## 📊 PRODUCT STATUS'LERİ

### Kullanıcı Önerileri
```
pending   → Kullanıcı gönderdi, admin görmedI
reviewing → Admin inceliyor
approved  → Admin onayladı → Ürün olarak sisteme girer
rejected  → Reddedildi
```

### Admin Ürünleri
```
draft            → Henüz yayınlanmadı
active           → Yayında, wishlist toplanıyor
moq_reached      → MoQ doldu, ödeme penceresi açık
payment_collecting → 48h ödeme dönemi
ordered          → Sipariş verildi
```

---

## 💰 FİYAT HESAPLAMA

### Formula
```
1. Unit cost TRY = unit_price_usd × usd_rate (50.00)
2. Shipping per unit = (total_shipping / moq) × usd_rate
3. Customs = unit_cost × customs_rate (35%)
4. KDV base = unit_cost + shipping + customs
5. KDV = kdv_base × 0.20 (20%)
6. Total cost = kdv_base + kdv
7. Margin = total_cost × margin_rate (30%)
8. Selling price = total_cost + margin
```

### Örnek
```
Girdi:
- Unit price: $800
- MoQ: 50
- Shipping: $200
- Customs: 35%
- Margin: 30%
- USD rate: ₺50.00

Çıktı:
- Unit cost: ₺40,000
- Shipping/unit: ₺200
- Customs: ₺14,000 (35%)
- KDV base: ₺54,200
- KDV: ₺10,840 (20%)
- Total cost: ₺65,040
- Margin: ₺19,512 (30%)
- Selling price: ₺84,552
```

---

## 🧪 TEST SENARYOLARI

### Senaryo 1: Admin Ürün Ekler

```bash
# 1. Admin login
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"admin123"}' | jq -r '.access_token')

# 2. Fiyat önizleme
curl -X POST http://localhost:8000/api/admin/calculate-price \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "unit_price_usd": 800,
    "moq": 50,
    "shipping_cost_usd": 200,
    "customs_rate": 0.35,
    "margin_rate": 0.30
  }'

# 3. Ürün ekle
PRODUCT_ID=$(curl -X POST http://localhost:8000/api/admin/products \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "iPhone 15 Pro Max 256GB",
    "description": "Apple iPhone 15 Pro Max",
    "category_id": null,
    "images": [],
    "supplier_name": "Shenzhen Tech Co",
    "alibaba_product_url": "https://...",
    "unit_price_usd": 800,
    "moq": 50,
    "lead_time_days": 30,
    "shipping_cost_usd": 200,
    "customs_rate": 0.35,
    "margin_rate": 0.30
  }' | jq -r '.id')

# 4. Yayınla
curl -X POST http://localhost:8000/api/admin/products/$PRODUCT_ID/publish \
  -H "Authorization: Bearer $TOKEN"

# 5. Public endpoint'ten kontrol et (artık görünür)
curl http://localhost:8000/api/v1/products
```

### Senaryo 2: Kullanıcı Öneri Gönderir

```bash
# 1. Kullanıcı login
USER_TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"user123"}' | jq -r '.access_token')

# 2. Ürün önerisi gönder
curl -X POST http://localhost:8000/api/v1/products/request \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Samsung S24 Ultra",
    "description": "512GB version",
    "expected_price_try": 45000
  }'

# 3. Admin önerileri görür
curl http://localhost:8000/api/admin/product-requests?status=pending \
  -H "Authorization: Bearer $TOKEN"

# 4. Admin onaylar
curl -X PATCH http://localhost:8000/api/admin/product-requests/{REQUEST_ID} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"approved"}'
```

---

## 📁 YENİ DOSYALAR

```
backend/app/
├── api/
│   ├── admin/
│   │   └── admin.py          ← YENİ: Admin endpoints
│   └── v1/endpoints/
│       ├── auth.py
│       ├── products.py        ← REVİZE EDİLDİ
│       └── wishlist.py
├── services/
│   ├── moq_service.py
│   └── price_service.py       ← YENİ: Fiyat hesaplama
└── schemas/
    └── schemas.py             ← REVİZE EDİLDİ: Yeni schema'lar
```

---

## ✅ CHECKLIST

Test etmen gerekenler:

### Admin İşlemleri
- [ ] Admin olarak login yapabildin mi?
- [ ] `/api/admin/calculate-price` çalışıyor mu?
- [ ] Ürün ekleyebildin mi?
- [ ] Draft status ile kaydediliyor mu?
- [ ] Publish yapabildin mi?
- [ ] Ürün active duruma geçti mi?

### Public İşlemler
- [ ] Kullanıcı olarak sadece active ürünleri görebiliyor musun?
- [ ] Draft ürünler gizli mi?
- [ ] Ürün önerisi gönderebiliyor musun?
- [ ] Admin önerileri görebiliyor mu?

### Fiyat Hesaplama
- [ ] Fiyat doğru hesaplanıyor mu?
- [ ] USD kuru 38.50 olarak mı alınıyor?
- [ ] Gümrük, KDV, marj doğru mu?

---

## 🐛 BİLİNEN SORUNLAR

- USD kuru şu an sabit (₺50.00) - TCMB API entegrasyonu yapılacak
- Admin user oluşturma endpoint'i yok (manuel DB'ye eklenmeli)
- Image upload henüz yok (URL olarak girilecek)

---

## 🔜 SONRAK​İ ADIMLAR

**Hafta 2 (Devam):**
- [ ] iyzico payment integration
- [ ] Celery tasks (email, cleanup)
- [ ] Email service + templates
- [ ] Admin panel HTML (artifact)

**Test et ve raporla!** 🚀
