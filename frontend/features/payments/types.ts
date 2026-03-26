export type PaymentStage =
  | "campaign_active"
  | "moq_reached"
  | "payment_confirmed"
  | "order_placed"
  | "shipping"
  | "delivered";

/** Matches backend PaymentEntryV2Response */
export interface PaymentEntry {
  id: string;              // participant_id
  campaign_id: string;
  campaign_title: string;
  campaign_image: string | null;
  quantity: number;
  total_amount: number;
  status: "joined" | "invited" | "paid" | "expired" | "cancelled";
  payment_deadline: string | null;
  stage: PaymentStage;
  lead_time_days?: number | null;
}
