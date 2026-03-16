export type PaymentStage =
  | "campaign_active"
  | "moq_reached"
  | "payment_confirmed"
  | "order_placed"
  | "shipping"
  | "delivered";

export interface PaymentEntry {
  id: string;
  request_id: string;
  product_title: string;
  product_image: string | null;
  quantity: number;
  /** Total amount due in Turkish Lira */
  total_amount: number;
  status: "waiting" | "notified" | "paid" | "expired" | "cancelled";
  payment_deadline: string | null;
  stage: PaymentStage;
  lead_time_days?: number | null;
}
