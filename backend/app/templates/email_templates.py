"""
Email Templates
"""
from typing import Dict
from datetime import datetime


class EmailTemplates:
    """Email HTML templates."""
    
    @staticmethod
    def get_base_template(content: str) -> str:
        """Base email template with styling."""
        return f"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #007bff;
        }}
        .header h1 {{
            color: #007bff;
            margin: 0;
        }}
        .button {{
            display: inline-block;
            padding: 12px 30px;
            background: #007bff;
            color: white !important;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            margin: 20px 0;
        }}
        .button:hover {{
            background: #0056b3;
        }}
        .info-box {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 12px;
        }}
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
        }}
        .success {{
            background: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛒 Toplu Alışveriş</h1>
        </div>
        {content}
        <div class="footer">
            <p>Bu email otomatik olarak gönderilmiştir.</p>
            <p>Sorularınız için: destek@toplualisveris.com</p>
        </div>
    </div>
</body>
</html>
"""
    
    @staticmethod
    def moq_reached(data: Dict) -> str:
        """MoQ reached - payment invitation email."""
        content = f"""
<h2>🎉 Harika Haber! Sipariş Hazır</h2>

<div class="success">
    <strong>{data['product_title']}</strong> için yeterli talep toplandı!
</div>

<p>Merhaba,</p>

<p><strong>{data['product_title']}</strong> ürünü için {data['moq']} kişilik hedef tamamlandı! 
Artık toplu siparişi verebiliriz.</p>

<div class="info-box">
    <h3>📦 Ürün Bilgileri</h3>
    <p><strong>Ürün:</strong> {data['product_title']}</p>
    <p><strong>Adet:</strong> {data['quantity']}</p>
    <p><strong>Birim Fiyat:</strong> ₺{data['unit_price']:,.2f}</p>
    <p><strong>Toplam:</strong> ₺{data['total_price']:,.2f}</p>
</div>

<div class="warning">
    <h3>⏰ ÖNEMLİ: 48 Saat İçinde Ödeme Yapın</h3>
    <p>Son ödeme tarihi: <strong>{data['deadline']}</strong></p>
    <p>Bu süre içinde ödeme yapmazsanız, siparişiniz iptal olacaktır.</p>
</div>

<div style="text-align: center;">
    <a href="{data['payment_url']}" class="button">
        💳 Ödeme Yap
    </a>
</div>

<p>Ödeme yaptıktan sonra siparişiniz kesinleşecek ve tedarikçiye iletilecektir.</p>

<p><strong>Teslim Süresi:</strong> {data['lead_time_days']} gün (ödeme sonrası)</p>

<p>İyi alışverişler dileriz! 🎁</p>
"""
        return EmailTemplates.get_base_template(content)
    
    @staticmethod
    def payment_reminder(data: Dict) -> str:
        """Payment reminder - 24h before deadline."""
        content = f"""
<h2>⏰ Ödeme Hatırlatması</h2>

<div class="warning">
    <strong>{data['product_title']}</strong> için ödeme süreniz dolmak üzere!
</div>

<p>Merhaba,</p>

<p><strong>{data['hours_remaining']} saat</strong> içinde ödeme yapmazsanız, 
siparişiniz iptal olacak.</p>

<div class="info-box">
    <p><strong>Ürün:</strong> {data['product_title']}</p>
    <p><strong>Toplam:</strong> ₺{data['total_price']:,.2f}</p>
    <p><strong>Son ödeme:</strong> {data['deadline']}</p>
</div>

<div style="text-align: center;">
    <a href="{data['payment_url']}" class="button">
        💳 Hemen Ödeme Yap
    </a>
</div>

<p>Ödeme yapmak istemiyorsanız, herhangi bir işlem yapmanıza gerek yok. 
Süre dolduğunda otomatik olarak iptal edilecektir.</p>
"""
        return EmailTemplates.get_base_template(content)
    
    @staticmethod
    def payment_success(data: Dict) -> str:
        """Payment successful confirmation."""
        content = f"""
<h2>✅ Ödeme Başarılı!</h2>

<div class="success">
    <strong>{data['product_title']}</strong> için ödemeniz alındı.
</div>

<p>Merhaba,</p>

<p>₺{data['total_price']:,.2f} tutarındaki ödemeniz başarıyla alındı. 
Siparişiniz kesinleşti!</p>

<div class="info-box">
    <h3>📦 Sipariş Detayları</h3>
    <p><strong>Sipariş No:</strong> #{data['order_id']}</p>
    <p><strong>Ürün:</strong> {data['product_title']}</p>
    <p><strong>Adet:</strong> {data['quantity']}</p>
    <p><strong>Tutar:</strong> ₺{data['total_price']:,.2f}</p>
    <p><strong>Tahmini Teslimat:</strong> {data['estimated_delivery']}</p>
</div>

<p>Toplu sipariş tamamlandığında tedarikçiye iletilecek ve 
{data['lead_time_days']} gün içinde kargoya verilecektir.</p>

<p>Kargo takip numarası elimize ulaştığında size bildireceğiz.</p>

<p>Teşekkür ederiz! 🎉</p>
"""
        return EmailTemplates.get_base_template(content)
    
    @staticmethod
    def moq_failed(data: Dict) -> str:
        """MoQ failed - not enough payments."""
        content = f"""
<h2>😔 Sipariş İptal Edildi</h2>

<div class="warning">
    <strong>{data['product_title']}</strong> için yeterli ödeme toplanamadı.
</div>

<p>Merhaba,</p>

<p>Maalesef <strong>{data['product_title']}</strong> için 48 saat içinde 
yeterli sayıda ödeme yapılmadı. Sipariş iptal edildi.</p>

<div class="info-box">
    <p><strong>Hedef:</strong> {data['moq']} kişi</p>
    <p><strong>Ödeme yapan:</strong> {data['paid_count']} kişi</p>
    <p><strong>Eksik:</strong> {data['missing_count']} kişi</p>
</div>

<p>Ürün tekrar aktif hale getirildi. İsterseniz yeniden wishlist'e ekleyebilirsiniz.</p>

<p>Bir sonraki fırsatta görüşmek üzere! 👋</p>
"""
        return EmailTemplates.get_base_template(content)
    
    @staticmethod
    def order_shipped(data: Dict) -> str:
        """Order shipped notification."""
        content = f"""
<h2>🚚 Siparişiniz Kargoya Verildi!</h2>

<div class="success">
    <strong>{data['product_title']}</strong> yolda!
</div>

<p>Merhaba,</p>

<p>Toplu siparişimiz tedarikçi tarafından gönderildi. 
Ürününüz yakında elinizde olacak!</p>

<div class="info-box">
    <h3>📦 Kargo Bilgileri</h3>
    <p><strong>Sipariş No:</strong> #{data['order_id']}</p>
    <p><strong>Kargo Şirketi:</strong> {data['carrier']}</p>
    <p><strong>Takip No:</strong> <strong>{data['tracking_number']}</strong></p>
    <p><strong>Tahmini Teslimat:</strong> {data['estimated_delivery']}</p>
</div>

<div style="text-align: center;">
    <a href="{data['tracking_url']}" class="button">
        📍 Kargoyu Takip Et
    </a>
</div>

<p>Kargo teslim alındıktan sonra lütfen ürünü kontrol edin. 
Herhangi bir sorun olursa 48 saat içinde bize bildirin.</p>

<p>İyi günler dileriz! 🎁</p>
"""
        return EmailTemplates.get_base_template(content)
