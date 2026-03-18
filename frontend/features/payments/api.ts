import { api } from "@/lib/api/client";
import { PaymentEntry } from "./types";

const PAYMENTS = "/api/v1/payments";

export async function getPaymentEntry(entryId: string): Promise<PaymentEntry> {
  return api.get<PaymentEntry>(`${PAYMENTS}/entry/${entryId}`);
}

export async function getStatusEntry(entryId: string): Promise<PaymentEntry> {
  return api.get<PaymentEntry>(`${PAYMENTS}/entry/${entryId}`);
}

export async function initiatePayment(entryId: string): Promise<PaymentEntry> {
  return api.post<PaymentEntry>(`${PAYMENTS}/initiate`, { entry_id: entryId });
}

/** Confirm (mock) payment — marks entry as paid on the backend. */
export async function markPaymentAsPaid(entryId: string): Promise<PaymentEntry> {
  return api.post<PaymentEntry>(`${PAYMENTS}/entry/${entryId}/confirm`);
}
