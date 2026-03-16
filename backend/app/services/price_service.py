"""
Price Calculation Service
USD to TRY conversion + customs + KDV + margin
"""
from decimal import Decimal
from typing import Optional
import httpx

from app.core.config import settings
from app.schemas.schemas import PriceBreakdown


class PriceCalculator:
    """Handle price calculations with customs, shipping, KDV, and margin."""

    async def get_usd_try_rate(self) -> Decimal:
        """
        Get current USD/TRY exchange rate.

        Priority:
          1. Live rate from TCMB EVDS API (requires TCMB_API_KEY in env – TODO)
          2. settings.USD_TRY_FALLBACK_RATE from environment / .env file

        TODO: Implement live TCMB EVDS integration once an API key is available.
              See: https://evds2.tcmb.gov.tr/help/videos/EVDS_Web_Service_Usage_Guide.pdf
        """
        fallback = Decimal(str(settings.USD_TRY_FALLBACK_RATE))
        try:
            # Placeholder for future TCMB API call
            # async with httpx.AsyncClient() as client:
            #     response = await client.get(...)
            #     rate = Decimal(str(response.json()["rate"]))
            #     return rate
            return fallback
        except Exception as e:
            print(f"USD rate fetch error: {e}")
            return fallback

    async def calculate_selling_price(
        self,
        unit_price_usd: float,
        moq: int,
        shipping_cost_usd: float = 0,
        customs_rate: float = 0.35,
        margin_rate: float = 0.30,
    ) -> PriceBreakdown:
        """
        Calculate final selling price in TRY.

        Formula:
        1. Unit cost TRY = unit_price_usd × usd_rate
        2. Shipping per unit = (total_shipping / moq) × usd_rate
        3. Customs = unit_cost × customs_rate
        4. KDV base = unit_cost + shipping + customs
        5. KDV = kdv_base × 0.20
        6. Total cost = kdv_base + kdv
        7. Selling price = total_cost × (1 + margin_rate)
        """
        usd_rate = await self.get_usd_try_rate()

        unit_price = Decimal(str(unit_price_usd))
        shipping = Decimal(str(shipping_cost_usd))
        customs_r = Decimal(str(customs_rate))
        margin_r = Decimal(str(margin_rate))
        moq_d = Decimal(str(moq))

        unit_price_try = unit_price * usd_rate
        shipping_per_unit = (shipping / moq_d) * usd_rate if moq > 0 else Decimal("0")
        customs_try = unit_price_try * customs_r
        kdv_base = unit_price_try + shipping_per_unit + customs_try
        kdv_try = kdv_base * Decimal("0.20")
        total_cost = kdv_base + kdv_try
        margin_try = total_cost * margin_r
        selling_price = total_cost + margin_try

        return PriceBreakdown(
            unit_price_usd=unit_price,
            unit_price_try=unit_price_try.quantize(Decimal("0.01")),
            shipping_per_unit_try=shipping_per_unit.quantize(Decimal("0.01")),
            customs_try=customs_try.quantize(Decimal("0.01")),
            kdv_base_try=kdv_base.quantize(Decimal("0.01")),
            kdv_try=kdv_try.quantize(Decimal("0.01")),
            total_cost_try=total_cost.quantize(Decimal("0.01")),
            margin_try=margin_try.quantize(Decimal("0.01")),
            selling_price_try=selling_price.quantize(Decimal("0.01")),
            usd_rate=usd_rate,
        )
