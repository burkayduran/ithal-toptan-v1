import { CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

interface WishlistSuccessNoticeProps {
  quantity: number;
  campaignTitle: string;
}

export default function WishlistSuccessNotice({ quantity, campaignTitle }: WishlistSuccessNoticeProps) {
  return (
    <div className="rounded-xl bg-green-50 border border-green-200 p-5 space-y-3">
      <div className="flex items-start gap-3">
        <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
        <div>
          <p className="font-semibold text-green-800">Bekleme listesine katıldınız!</p>
          <p className="text-sm text-green-700 mt-0.5">
            <strong>{quantity} adet</strong> için kaydınız alındı. MOQ dolduğunda sizi bilgilendireceğiz.
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
