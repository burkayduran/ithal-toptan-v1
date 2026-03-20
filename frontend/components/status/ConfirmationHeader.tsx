import { cn } from "@/lib/utils";
import StatusBadge from "@/components/campaign/StatusBadge";
import { CheckCircle2, Clock, XCircle } from "lucide-react";
import type { ParticipantStatus } from "@/features/wishlist/types";

interface ConfirmationHeaderProps {
  entryStatus: ParticipantStatus;
  productTitle: string;
}

const CONFIG: Record<
  ParticipantStatus,
  { icon: React.ElementType; iconColor: string; heading: string; subtext: string }
> = {
  paid: {
    icon: CheckCircle2,
    iconColor: "text-green-500",
    heading: "Ödemeniz Alındı",
    subtext: "Siparişiniz işleme alındı. Güncellemeler e-posta ile iletilecek.",
  },
  invited: {
    icon: Clock,
    iconColor: "text-amber-500",
    heading: "Ödeme Bekleniyor",
    subtext: "Aşağıdaki süre dolmadan ödemenizi tamamlayın.",
  },
  joined: {
    icon: Clock,
    iconColor: "text-blue-500",
    heading: "Bekleme Listesinde",
    subtext: "Hedef sayıya ulaşıldığında ödeme bildirimi alacaksınız.",
  },
  expired: {
    icon: XCircle,
    iconColor: "text-red-500",
    heading: "Ödeme Süresi Doldu",
    subtext: "Ne yazık ki ödeme penceresi kapandı. Bir sonraki turda tekrar katılabilirsiniz.",
  },
  cancelled: {
    icon: XCircle,
    iconColor: "text-red-500",
    heading: "İptal Edildi",
    subtext: "Bu kayıt iptal edildi.",
  },
};

export default function ConfirmationHeader({ entryStatus, productTitle }: ConfirmationHeaderProps) {
  const { icon: Icon, iconColor, heading, subtext } = CONFIG[entryStatus] ?? CONFIG.joined;
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <Icon className={cn("h-8 w-8 shrink-0", iconColor)} />
        <div>
          <h1 className="text-xl font-bold text-gray-900">{heading}</h1>
          <p className="text-sm text-gray-500 line-clamp-1">{productTitle}</p>
        </div>
      </div>
      <StatusBadge status={entryStatus} />
      <p className="text-sm text-gray-600">{subtext}</p>
    </div>
  );
}
