import { PaymentEntry } from "./types";

const HOUR = 60 * 60 * 1000;

/** Keyed by entryId for O(1) lookup on payment/status pages */
export const MOCK_PAYMENT_ENTRIES: Record<string, PaymentEntry> = {
  "entry-notified-1": {
    id: "entry-notified-1",
    request_id: "req-001",
    product_title: "Apple AirPods Pro 2. Nesil",
    product_image:
      "https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=800&q=80",
    quantity: 2,
    total_amount: 3200,
    status: "notified",
    payment_deadline: new Date(Date.now() + 20 * HOUR).toISOString(),
    stage: "moq_reached",
    lead_time_days: 21,
  },
  "entry-paid-1": {
    id: "entry-paid-1",
    request_id: "req-002",
    product_title: "Sony WH-1000XM5 Kulaklık",
    product_image:
      "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&q=80",
    quantity: 1,
    total_amount: 1800,
    status: "paid",
    payment_deadline: null,
    stage: "payment_confirmed",
    lead_time_days: 14,
  },
  "entry-expired-1": {
    id: "entry-expired-1",
    request_id: "req-003",
    product_title: "Garmin Fenix 7 Akıllı Saat",
    product_image:
      "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80",
    quantity: 1,
    total_amount: 5500,
    status: "expired",
    payment_deadline: new Date(Date.now() - 2 * HOUR).toISOString(),
    stage: "moq_reached",
    lead_time_days: 28,
  },
  "entry-shipping-1": {
    id: "entry-shipping-1",
    request_id: "req-004",
    product_title: "Dyson V15 Detect Elektrikli Süpürge",
    product_image:
      "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&q=80",
    quantity: 1,
    total_amount: 4200,
    status: "paid",
    payment_deadline: null,
    stage: "shipping",
    lead_time_days: 7,
  },
};

export function getMockPaymentEntry(entryId: string): PaymentEntry | null {
  return MOCK_PAYMENT_ENTRIES[entryId] ?? null;
}
