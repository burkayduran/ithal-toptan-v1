/** Participant status values (matches backend ParticipantStatus) */
export type ParticipantStatus = "joined" | "invited" | "paid" | "expired" | "cancelled";

/** Matches backend ParticipantResponse */
export interface Participant {
  id: string;
  campaign_id: string;
  user_id: string;
  quantity: number;
  status: ParticipantStatus;
  joined_at: string;
  invited_at: string | null;
  payment_deadline: string | null;
  paid_at: string | null;
  campaign_title: string | null;
  campaign_image: string | null;
  campaign_status: string | null;
  selling_price_try: number | null;
  total_amount: number | null;
  moq_fill_percentage: number | null;
}
