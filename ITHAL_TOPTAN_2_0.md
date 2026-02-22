# İthal Toptan 2.0

İthal Toptan 2.0, mevcut backend çekirdeğinin yeniden markalanmış ve üretim odağı güçlendirilmiş sürümüdür.

## Bu güncellemede yapılanlar
- Proje varsayılan uygulama adı `İthal Toptan 2.0` olarak güncellendi.
- Uygulama versiyonu ayarlanabilir hale getirildi (`APP_VERSION`) ve varsayılan değer `2.0.0` yapıldı.
- API metadata ve health endpoint versiyonu artık konfigürasyondan okunuyor.

## 2.0 yol haritası
1. **Sipariş Yaşam Döngüsü**: ödeme doğrulama, parça ödeme, iade akışları.
2. **Tedarikçi Modülü**: teklif karşılaştırma, performans skorlama, SLA takibi.
3. **Operasyon Paneli**: durum panosu, manuel override, gecikme alarmı.
4. **Gözlemlenebilirlik**: structured logging, tracing, hata bütçesi metrikleri.
5. **Test Güvencesi**: API contract testleri ve MoQ yarış durumları için eşzamanlılık testleri.

## Hızlı başlangıç (2.0)
```bash
cp backend/.env.example backend/.env
# APP_NAME="İthal Toptan 2.0"
# APP_VERSION=2.0.0

docker compose up -d
```
