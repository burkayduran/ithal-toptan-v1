# 🚀 HIZLI BAŞLANGIÇ

## 5 Dakikada Çalıştır

### 1️⃣ Zip'i Aç
```bash
unzip toplu-alisveris-v2.zip
cd toplu-alisveris
```

### 2️⃣ Docker ile Başlat
```bash
docker compose up -d
```

### 3️⃣ Test Et
```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/api/docs
```

**✅ Hazır! API çalışıyor.**

---

## 📖 Temel Kullanım

### Adım 1: Kullanıcı Kaydı
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email":"test@test.com",
    "password":"test123",
    "full_name":"Test User"
  }'
```

**Cevap:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Token'ı kaydet!**

---

### Adım 2: Ürün Talebi Oluştur
```bash
TOKEN="eyJhbGciOiJIUzI1NiIs..."  # Yukarıdaki token

curl -X POST http://localhost:8000/api/v1/products \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"iPhone 15 Pro Max",
    "description":"256GB, Titanyum",
    "expected_price_try":45000
  }'
```

**Cevap:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "iPhone 15 Pro Max",
  "status": "pending",
  ...
}
```

**Product ID'yi kaydet!**

---

### Adım 3: Wishlist'e Ekle
```bash
PRODUCT_ID="550e8400-e29b-41d4-a716-446655440000"

curl -X POST http://localhost:8000/api/v1/wishlist/add \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id":"'$PRODUCT_ID'",
    "quantity":1
  }'
```

**Cevap:**
```json
{
  "message": "Added to wishlist"
}
```

---

### Adım 4: MoQ Progress Kontrol Et
```bash
curl http://localhost:8000/api/v1/wishlist/progress/$PRODUCT_ID
```

**Cevap:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "current": 1,
  "target": 50,
  "percentage": 2.0,
  "selling_price_try": null
}
```

---

## 🎯 Sonraki Adımlar

### Frontend'de Real-time Progress Bar
```html
<!DOCTYPE html>
<html>
<body>
  <div>MoQ Progress: <span id="count">0</span> / 50</div>
  <progress id="bar" max="50" value="0"></progress>

  <script>
    const productId = '550e8400-e29b-41d4-a716-446655440000';
    const eventSource = new EventSource(`http://localhost:8000/api/v1/moq/progress/${productId}`);
    
    eventSource.onmessage = (event) => {
      const count = event.data;
      document.getElementById('count').textContent = count;
      document.getElementById('bar').value = count;
    };
  </script>
</body>
</html>
```

---

## 🐛 Sorun Giderme

### Port zaten kullanımda
```bash
docker compose down
sudo lsof -i :8000  # Process'i bul
sudo kill -9 PID    # Kill et
```

### Database connection error
```bash
docker compose logs db
# PostgreSQL loglarını kontrol et
```

### Redis connection error
```bash
docker compose logs redis
# Redis loglarını kontrol et
```

### API başlamıyor
```bash
docker compose logs api
# Backend loglarını kontrol et
# Syntax error var mı?
```

### Tüm servisleri yeniden başlat
```bash
docker compose down -v  # Volumes'ı da sil
docker compose up -d
```

---

## 📚 Daha Fazla Bilgi

- **Full README**: `README.md`
- **API Docs**: http://localhost:8000/api/docs
- **Redoc**: http://localhost:8000/api/redoc

---

## ✅ Checklist

Test etmen gerekenler:

- [ ] Docker başarıyla başladı mı?
- [ ] Health check çalışıyor mu?
- [ ] Register yapabildin mi?
- [ ] Login yapabildin mi?
- [ ] Token aldın mı?
- [ ] Ürün oluşturabildin mi?
- [ ] Wishlist'e ekleyebildin mi?
- [ ] MoQ progress görüntüleyebildin mi?
- [ ] SSE stream çalışıyor mu? (browser'da test et)

**Herhangi bir adımda hata varsa:**
1. Error mesajını kopyala
2. Stack trace'i paylaş
3. Docker logs'u paylaş
4. Birlikte debug ederiz!

---

## 🎉 Başarılı!

Backend core hazır. Şimdi:
1. Bu adımları test et
2. Hataları raporla
3. Sonraki adıma geçelim (Admin endpoints + iyzico)

İyi testler! 🚀
