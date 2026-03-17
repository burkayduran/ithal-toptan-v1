import { PaymentEntry } from "./types";
import { getMockPaymentEntry } from "./mock";

export async function getPaymentEntry(entryId: string): Promise<PaymentEntry> {
  const entry = getMockPaymentEntry(entryId);
  if (!entry) throw new Error("Ödeme kaydı bulunamadı.");
  return entry;
}

export async function getStatusEntry(entryId: string): Promise<PaymentEntry> {
  const entry = getMockPaymentEntry(entryId);
  if (!entry) throw new Error("Durum bilgisi bulunamadı.");
  return entry;
}

/** Mock-only: simulate confirming payment for a notified entry */
export async function markPaymentAsPaid(entryId: string): Promise<PaymentEntry> {
  const entry = getMockPaymentEntry(entryId);
  if (!entry) throw new Error("Ödeme kaydı bulunamadı.");
  return {
    ...entry,
    status: "paid",
    stage: "payment_confirmed",
    payment_deadline: null,
  };
}
