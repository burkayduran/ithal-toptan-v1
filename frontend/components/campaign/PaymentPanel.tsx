"use client";

import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils/formatCurrency";
import { Loader2, CreditCard, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useConfirmPayment } from "@/features/payments/hooks";

interface PaymentPanelProps {
  participantId: string;
  totalAmount: number;
  isExpired: boolean;
  isPaid: boolean;
}

export default function PaymentPanel({
  participantId,
  totalAmount,
  isExpired,
  isPaid,
}: PaymentPanelProps) {
  const router = useRouter();
  const { mutate: confirm, isPending } = useConfirmPayment();

  const handlePay = () => {
    confirm(participantId, {
      onSuccess: () => router.push(`/status/${participantId}`),
    });
  };

  if (isPaid) {
    return (
      <div className="rounded-xl border border-green-200 bg-green-50 p-5 space-y-3">
        <div className="flex items-center gap-2 text-green-700">
          <ShieldCheck className="h-5 w-5" />
          <p className="font-semibold">Ödeme tamamlandı</p>
        </div>
        <p className="text-sm text-green-600">
          Ödemeniz onaylandı. Siparişiniz işleme alındı.
        </p>
        <Link href={`/status/${participantId}`}>
          <Button variant="outline" className="w-full border-green-300 text-green-700 hover:bg-green-100">
            Durumu Gör →
          </Button>
        </Link>
      </div>
    );
  }

  if (isExpired) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5 space-y-3">
        <p className="font-semibold text-red-700">Ödeme süresi doldu</p>
        <p className="text-sm text-red-600">
          Ödeme pencereniz kapandı. Bir sonraki turda tekrar katılabilirsiniz.
        </p>
        <Button variant="outline" className="w-full opacity-50" disabled>
          <CreditCard className="h-4 w-4 mr-2" />
          Ödeme Yap
        </Button>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">Ödenecek Tutar</p>
        <p className="text-2xl font-bold text-gray-900">{formatCurrency(totalAmount)}</p>
      </div>

      <p className="text-xs text-gray-400">
        Ödemeniz yerini kesinleştirir. Hedef sayı dolduğunda sipariş verilir.
      </p>

      <Button
        className="w-full gap-2"
        size="lg"
        onClick={handlePay}
        disabled={isPending}
      >
        {isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <CreditCard className="h-4 w-4" />
        )}
        {isPending ? "İşleniyor..." : "Ödemeyi Tamamla"}
      </Button>

      <div className="flex items-center gap-1.5 text-xs text-gray-400 justify-center">
        <ShieldCheck className="h-3.5 w-3.5" />
        <span>256-bit SSL ile korunan ödeme</span>
      </div>
    </div>
  );
}
