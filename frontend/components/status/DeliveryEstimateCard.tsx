import { Truck } from "lucide-react";

interface DeliveryEstimateCardProps {
  leadTimeDays: number;
  /** If provided, show an absolute estimate based on order date */
  orderedAt?: string | null;
}

function addBusinessDays(from: Date, days: number): Date {
  const result = new Date(from);
  result.setDate(result.getDate() + days);
  return result;
}

export default function DeliveryEstimateCard({
  leadTimeDays,
  orderedAt,
}: DeliveryEstimateCardProps) {
  const estimateDate = orderedAt
    ? addBusinessDays(new Date(orderedAt), leadTimeDays)
    : null;

  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 p-5 flex items-start gap-4">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-100">
        <Truck className="h-5 w-5 text-blue-600" />
      </div>
      <div>
        <p className="font-semibold text-gray-900 text-sm">Tahmini Teslimat</p>
        {estimateDate ? (
          <p className="text-sm text-gray-600 mt-0.5">
            {estimateDate.toLocaleDateString("tr-TR", {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </p>
        ) : (
          <p className="text-sm text-gray-600 mt-0.5">
            Sipariş tarihinden itibaren yaklaşık{" "}
            <strong>{leadTimeDays} gün</strong>
          </p>
        )}
        <p className="text-xs text-gray-400 mt-1">
          Teslimat süresi gümrük işlemlerine bağlı olarak değişebilir.
        </p>
      </div>
    </div>
  );
}
