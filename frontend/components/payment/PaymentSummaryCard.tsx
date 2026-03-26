import { formatCurrency } from "@/lib/utils/formatCurrency";
import { Separator } from "@/components/ui/separator";
import { Package } from "lucide-react";

interface PaymentSummaryCardProps {
  productTitle: string;
  quantity: number;
  pricePerUnit: number;
  totalAmount: number;
}

export default function PaymentSummaryCard({
  productTitle,
  quantity,
  pricePerUnit,
  totalAmount,
}: PaymentSummaryCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
      <h3 className="font-semibold text-gray-900 text-sm flex items-center gap-2">
        <Package className="h-4 w-4 text-gray-400" />
        Sipariş Özeti
      </h3>

      <div className="space-y-2 text-sm">
        <div className="flex justify-between text-gray-600">
          <span className="line-clamp-1 flex-1 pr-4">{productTitle}</span>
          <span className="shrink-0">{formatCurrency(pricePerUnit)}</span>
        </div>
        <div className="flex justify-between text-gray-500">
          <span>Adet</span>
          <span>× {quantity}</span>
        </div>
      </div>

      <Separator />

      <div className="flex justify-between font-bold text-gray-900">
        <span>Toplam</span>
        <span className="text-lg">{formatCurrency(totalAmount)}</span>
      </div>
    </div>
  );
}
