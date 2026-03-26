import { CheckCircle2, CreditCard } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

interface WishlistSuccessNoticeProps {
  quantity: number;
  campaignTitle: string;
  /** Campaign status at join time — determines messaging */
  campaignStatus?: string;
}

export default function WishlistSuccessNotice({
  quantity,
  campaignTitle,
  campaignStatus,
}: WishlistSuccessNoticeProps) {
  const isPaymentPhase = campaignStatus === "moq_reached";

  if (isPaymentPhase) {
    return (
      <div className="rounded-xl bg-amber-50 border border-amber-200 p-5 space-y-3">
        <div className="flex items-start gap-3">
          <CreditCard className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-semibold text-amber-800">Ödeme sürecine alındınız!</p>
            <p className="text-sm text-amber-700 mt-0.5">
              <strong>{campaignTitle}</strong> için <strong>{quantity} adet</strong> kaydınız alındı.
              Ödeme davetiniz gönderilecek — lütfen siparişlerinizi takip edin.
            </p>
          </div>
        </div>
        <Link href="/my-campaigns">
          <Button variant="outline" size="sm" className="border-amber-300 text-amber-700 hover:bg-amber-100">
            Siparişlerimi Gör →
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-green-50 border border-green-200 p-5 space-y-3">
      <div className="flex items-start gap-3">
        <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
        <div>
          <p className="font-semibold text-green-800">Katılım listendesiniz!</p>
          <p className="text-sm text-green-700 mt-0.5">
            <strong>{campaignTitle}</strong> için <strong>{quantity} adet</strong> kaydınız alındı.
            Yeterli talep oluştuğunda ödeme daveti alacaksınız.
          </p>
        </div>
      </div>
      <Link href="/my-campaigns">
        <Button variant="outline" size="sm" className="border-green-300 text-green-700 hover:bg-green-100">
          Siparişlerimi Gör →
        </Button>
      </Link>
    </div>
  );
}
