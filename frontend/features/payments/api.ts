import { api } from "@/lib/api/client";
import { PaymentEntry } from "./types";

const V2 = "/api/v2";

export async function getPaymentEntry(participantId: string): Promise<PaymentEntry> {
  return api.get<PaymentEntry>(`${V2}/payments/${participantId}`);
}

export async function getStatusEntry(participantId: string): Promise<PaymentEntry> {
  return api.get<PaymentEntry>(`${V2}/payments/${participantId}`);
}

export async function confirmPayment(participantId: string): Promise<PaymentEntry> {
  return api.post<PaymentEntry>(`${V2}/payments/${participantId}/confirm`);
}
