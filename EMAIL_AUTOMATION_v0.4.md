# 📧 EMAIL OTOMASYONU - v0.4.0

## ✅ EKLENDİ

### 1. Email Service (Resend)
- ✅ Resend API entegrasyonu
- ✅ Email gönderimi (tek/toplu)
- ✅ HTML template desteği

### 2. Email Templates
- ✅ MoQ Reached (ödeme daveti)
- ✅ Payment Reminder (24h kala)
- ✅ Payment Success (onay)
- ✅ MoQ Failed (iptal)
- ✅ Order Shipped (kargo bilgisi)

### 3. Celery Tasks
- ✅ `send_moq_reached_email` - MoQ dolunca
- ✅ `send_payment_reminders` - Her 6 saatte (Beat)
- ✅ `send_payment_success_email` - Ödeme sonrası
- ✅ `send_moq_failed_email` - MoQ tutmadıysa
- ✅ `cleanup_expired_entries` - 48h sonra
- ✅ `cleanup_all_expired` - Her 30dk (Beat)

### 4. Docker Services
- ✅ Celery Worker
- ✅ Celery Beat (Scheduler)
- ✅ Flower (Monitoring)

---

## 🚀 KURULUM

### 1. Resend API Key Al

```bash
# https://resend.com adresinden API key al
# Ücretsiz plan: 100 email/gün
```

### 2. Environment Variables

```bash
# .env dosyasına ekle
RESEND_API_KEY=re_xxxxxxxxxxxxx
RESEND_FROM_EMAIL=noreply@toplualisveris.com
```

**ÖNEMLİ:** `RESEND_FROM_EMAIL` domain'i Resend'de verify edilmiş olmalı!

### 3. Docker Compose

```bash
# Tüm servisleri başlat
docker compose up -d

# Servisler:
# - api (FastAPI)
# - celery_worker (Background tasks)
# - celery_beat (Scheduler)
# - flower (Monitoring - http://localhost:5555)
```

### 4. Kontrol Et

```bash
# Celery worker logları
docker compose logs -f celery_worker

# Celery beat logları
docker compose logs -f celery_beat

# Flower monitoring
open http://localhost:5555
```

---

## 📊 EMAIL AKIŞI

### 1. MoQ Doldu

```
Kullanıcı wishlist ekler
├─ MoQ counter artış
├─ Counter >= MoQ?
│  ├─ YES:
│  │  ├─ Product status: moq_reached
│  │  ├─ Wishlist entries: notified
│  │  ├─ Celery task: send_moq_reached_email ✉️
│  │  │  └─ 3 user → 3 email gönderilir
│  │  └─ Celery task (delayed 48h): cleanup_expired_entries
│  └─ NO: Continue
```

**Email İçeriği:**
- 🎉 Sipariş hazır!
- Ödeme linki
- 48 saat deadline
- Ürün bilgileri
- Toplam fiyat

### 2. Payment Reminder

```
Celery Beat (Her 6 saatte)
└─ Celery task: send_payment_reminders
   ├─ Deadline < 24h olan entry'leri bul
   ├─ Her birine reminder email gönder ✉️
   └─ Notification kaydı oluştur
```

**Email İçeriği:**
- ⏰ 12 saat kaldı!
- Ödeme linki
- Deadline

### 3. Payment Success

```
User ödeme yapar (iyzico callback)
└─ Entry status: paid
   └─ Celery task: send_payment_success_email ✉️
```

**Email İçeriği:**
- ✅ Ödemeniz alındı
- Sipariş no
- Tahmini teslimat

### 4. MoQ Failed

```
Celery (48h sonra): cleanup_expired_entries
├─ Paid count >= MoQ?
│  ├─ NO:
│  │  ├─ Product status: active (reset)
│  │  ├─ Entries: waiting (reset)
│  │  └─ Celery task: send_moq_failed_email ✉️
│  └─ YES:
│     └─ Batch order oluştur
```

**Email İçeriği:**
- 😔 Sipariş iptal edildi
- Yeterli ödeme toplanamadı
- Ürün tekrar aktif

---

## 🧪 TEST

### Test 1: MoQ Email (Manuel)

```python
# Django shell / Python console
from app.tasks.email_tasks import send_moq_reached_email
from datetime import datetime, timedelta

deadline = (datetime.utcnow() + timedelta(hours=48)).isoformat()

send_moq_reached_email.delay(
    "PRODUCT_UUID",
    deadline
)

# Celery worker logunda görmelisin:
# "📧 Sending MoQ reached emails to 3 users..."
# "✅ Sent 3 MoQ reached emails"
```

### Test 2: Payment Reminder (Manuel)

```python
from app.tasks.email_tasks import send_payment_reminders

send_payment_reminders.delay()

# Celery worker logunda:
# "📧 Sending payment reminders to X users..."
```

### Test 3: Cleanup (Manuel)

```python
from app.tasks.moq_tasks import cleanup_expired_entries

cleanup_expired_entries.delay("PRODUCT_UUID")

# Celery worker logunda:
# "🧹 Cleaning up expired entries..."
# "✅ MoQ success! Product ordered"
# veya
# "❌ MoQ failed! Product reset to active"
```

### Test 4: End-to-End

```bash
# 1. Admin ürün ekle (MoQ: 3)
# 2. 3 user wishlist ekle
# 3. MoQ doldu!
# 4. Celery worker log:
#    "📧 Sending MoQ reached emails to 3 users..."
# 5. Email gelen kutusunu kontrol et
# 6. 48 saat bekle (ya da manuel cleanup çağır)
# 7. Ödeme yapan < 3 ise:
#    "❌ MoQ failed! Product reset"
#    "📧 Sending MoQ failed emails..."
```

---

## 🔍 MONİTORİNG

### Flower Dashboard

```bash
# Flower aç
open http://localhost:5555

# Görüntülenen:
# - Active tasks
# - Completed tasks
# - Failed tasks
# - Task execution time
# - Worker status
```

### Celery Logs

```bash
# Worker logs
docker compose logs -f celery_worker

# Beat logs
docker compose logs -f celery_beat

# Filter by keyword
docker compose logs celery_worker | grep "📧"
```

### Database

```sql
-- Gönderilen notification'ları gör
SELECT * FROM notifications 
WHERE status = 'sent' 
ORDER BY sent_at DESC;

-- Pending notification'lar
SELECT * FROM notifications 
WHERE status = 'pending';

-- Email gönderim istatistikleri
SELECT type, COUNT(*), status
FROM notifications
GROUP BY type, status;
```

---

## ⚙️ CELERY BEAT SCHEDULE

### Periyodik Tasklar

```python
# Her 30 dakikada
"cleanup-expired-entries": {
    "task": "app.tasks.moq_tasks.cleanup_all_expired",
    "schedule": crontab(minute="*/30"),
}

# Her 6 saatte
"send-payment-reminders": {
    "task": "app.tasks.email_tasks.send_payment_reminders",
    "schedule": crontab(minute=0, hour="*/6"),
}
```

### Schedule Değiştirme

```python
# backend/app/tasks/celery_app.py

# Örnek: Her saat yerine her 3 saatte
"send-payment-reminders": {
    "task": "...",
    "schedule": crontab(minute=0, hour="*/3"),  # Her 3 saat
}

# Örnek: Sadece gece 02:00'da
"cleanup-expired-entries": {
    "task": "...",
    "schedule": crontab(minute=0, hour=2),  # 02:00
}
```

---

## 🐛 SORUN GİDERME

### Email Gitmiyor

**1. RESEND_API_KEY kontrol et:**
```bash
docker compose logs api | grep RESEND
# API key set edilmiş mi?
```

**2. Resend dashboard kontrol et:**
```
https://resend.com/emails
# Email gönderilmiş mi?
# Spam'e düşmüş mü?
```

**3. Celery worker çalışıyor mu:**
```bash
docker compose ps
# celery_worker: Up
```

**4. Task queued mu:**
```bash
# Flower'da kontrol et
open http://localhost:5555/tasks
```

### Celery Task Çalışmıyor

**1. Worker logs:**
```bash
docker compose logs celery_worker | tail -50
# Error var mı?
```

**2. Redis connection:**
```bash
docker exec -it toplu_redis redis-cli PING
# PONG dönmeli
```

**3. Task retry:**
```python
# Task'ı manuel çağır
from app.tasks.email_tasks import send_moq_reached_email
send_moq_reached_email.delay("UUID", "2024-01-01T00:00:00")
```

### Beat Schedule Çalışmıyor

**1. Beat çalışıyor mu:**
```bash
docker compose ps celery_beat
# Up durumda olmalı
```

**2. Beat logs:**
```bash
docker compose logs celery_beat
# "Scheduler: Sending due task..." görmelisin
```

**3. Timezone:**
```python
# celery_app.py
timezone="Europe/Istanbul",  # Doğru timezone?
```

---

## 📝 EKSİK (TODO)

1. **Email Templates İyileştirme**
   - Brand logo ekle
   - Mobile responsive test et
   - Dark mode support

2. **Email Tracking**
   - Open tracking
   - Click tracking
   - Bounce handling

3. **SMS Support**
   - Twilio/Netgsm entegrasyonu
   - SMS templates
   - SMS task'leri

4. **Rate Limiting**
   - Email flood protection
   - Per-user limits

---

## 🎯 SONUÇ

✅ **Email otomasyonu tamam!**

**Çalışan:**
- MoQ dolunca otomatik email ✉️
- 48h sonra otomatik cleanup 🧹
- Payment reminder (6 saatte bir) ⏰
- Success/failed notifications ✅

**Eksik:**
- iyzico ödeme (Hafta 2 devam)
- SMS notifications (optional)

**Sonraki adım:** iyzico payment integration 💳
