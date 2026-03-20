# Toplu Alışveriş Platformu

Group-buy (toplu alım) platformu — FastAPI + Next.js.

## API Endpoints

### Auth (V1 — paylaşımlı)
- `POST /api/v1/auth/register` - Kayıt
- `POST /api/v1/auth/login` - Giriş
- `GET /api/v1/auth/me` - Profil
- `PATCH /api/v1/auth/me` - Profil güncelleme

### Campaigns (V2 — Public)
- `GET /api/v2/campaigns` - Aktif kampanyalar (paginated)
- `GET /api/v2/campaigns/{id}` - Kampanya detayı
- `GET /api/v2/campaigns/{id}/similar` - Benzer kampanyalar
- `GET /api/v2/campaigns/{id}/progress` - MOQ ilerleme
- `GET /api/v2/moq/progress/{id}` - SSE real-time progress

### Campaigns (V2 — Auth gerekli)
- `POST /api/v2/campaigns/{id}/join` - Kampanyaya katıl
- `DELETE /api/v2/campaigns/{id}/leave` - Kampanyadan ayrıl
- `GET /api/v2/campaigns/my` - Katılımlarım

### Payments (V2)
- `GET /api/v2/payments/{participant_id}` - Ödeme/durum görüntüle
- `POST /api/v2/payments/{participant_id}/confirm` - Ödeme onayla

### Suggestions (V2)
- `POST /api/v2/suggestions` - Ürün önerisi gönder

### Admin (V2)
- `POST /api/v2/admin/campaigns` - Kampanya oluştur
- `POST /api/v2/admin/campaigns/{id}/publish` - Yayınla
- `PATCH /api/v2/admin/campaigns/{id}` - Güncelle
- `GET /api/v2/admin/campaigns` - Tüm kampanyalar
- `GET /api/v2/admin/campaigns/{id}` - Kampanya detayı
- `POST /api/v2/admin/campaigns/bulk-publish` - Toplu yayınla
- `POST /api/v2/admin/campaigns/bulk-cancel` - Toplu iptal
- `GET /api/v2/admin/suggestions` - Öneriler
- `PATCH /api/v2/admin/suggestions/{id}` - Öneri güncelle
- `GET /api/v2/admin/categories` - Kategoriler
- `POST /api/v2/admin/categories` - Kategori ekle
- `PATCH /api/v2/admin/categories/{id}` - Kategori güncelle
- `DELETE /api/v2/admin/categories/{id}` - Kategori sil
- `POST /api/v2/admin/calculate-price` - Fiyat önizleme

## MoQ Service
- Redis atomic counter (race condition safe)
- Auto-trigger when MoQ reached
- 48-hour payment window
- Expired entry cleanup
- Procurement order creation
- Real-time pub/sub for SSE

## İş Akışı

```
1. User joins campaign
   └─> Redis counter increments (atomic)

2. Counter >= MoQ threshold?
   ├─> YES: Trigger payment phase
   │   ├─> All "joined" → "invited"
   │   ├─> Set 48h deadline
   │   └─> Send email notifications
   └─> NO: Continue collecting

3. After 48 hours (Celery cleanup task)
   ├─> Mark expired participants
   ├─> Count paid participants
   └─> paid_count >= MoQ?
       ├─> YES: Create procurement order
       └─> NO: Reset to "active"
```

## Hızlı Başlangıç

### Docker ile Çalıştırma (Önerilen)

```bash
docker compose up -d

# API: http://localhost:8000
# Docs: http://localhost:8000/api/docs
```

### Local Development

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# API server
uvicorn app.main:app --reload --port 8000

# Celery worker (ayrı terminal)
celery -A app.tasks.celery_app worker --loglevel=info

# Celery beat (ayrı terminal)
celery -A app.tasks.celery_app beat --loglevel=info
```

## Veritabanı

### Active Tables
- users, categories, products, campaigns, campaign_participants
- payment_transactions, procurement_orders, supplier_offers
- product_suggestions, campaign_status_history, participant_status_history
- notifications, suppliers

### Legacy (Archived)
- legacy_product_requests, legacy_wishlist_entries
- legacy_payments, legacy_batch_orders

## Test

```bash
cd backend
pytest tests/ -v
```
