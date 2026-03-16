import Image from "next/image";
import Link from "next/link";
import { WishlistEntry } from "@/features/wishlist/types";
import { Button } from "@/components/ui/button";
import StatusBadge from "@/components/campaign/StatusBadge";
import CountdownBlock from "@/components/campaign/CountdownBlock";
import ProgressBlock from "@/components/campaign/ProgressBlock";
import { formatCurrency } from "@/lib/utils/formatCurrency";
import { useRemoveFromWishlist } from "@/features/wishlist/hooks";
import { Loader2, Trash2 } from "lucide-react";

const PLACEHOLDER_IMG =
  "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80";

interface MyCampaignCardProps {
  entry: WishlistEntry;
}

export default function MyCampaignCard({ entry }: MyCampaignCardProps) {
  const thumbnail = entry.product_image ?? PLACEHOLDER_IMG;
  const title = entry.product_title ?? "Ürün";
  const { mutate: remove, isPending: isRemoving } = useRemoveFromWishlist();

  const canRemove = entry.status === "waiting" || entry.status === "expired";

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-sm transition-shadow space-y-4">
      {/* Top: image + title + badge */}
      <div className="flex gap-4">
        <div className="relative w-20 h-20 rounded-lg overflow-hidden flex-shrink-0 bg-gray-100">
          <Image src={thumbnail} alt={title} fill className="object-cover" sizes="80px" />
        </div>

        <div className="flex-1 min-w-0 space-y-1.5">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-semibold text-gray-900 text-sm leading-snug line-clamp-2 flex-1">
              {title}
            </h3>
            <StatusBadge status={entry.status} className="shrink-0" />
          </div>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
            <span>{entry.quantity} adet</span>
            {entry.selling_price_try != null && (
              <>
                <span className="text-gray-300">·</span>
                <span className="font-medium text-gray-700">
                  {formatCurrency(entry.selling_price_try)} / adet
                </span>
              </>
            )}
            {entry.total_amount != null && (
              <>
                <span className="text-gray-300">·</span>
                <span className="font-semibold text-gray-900">
                  Toplam: {formatCurrency(entry.total_amount)}
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Middle: progress or countdown */}
      {entry.status === "waiting" &&
        entry.moq_fill_percentage != null && (
          <ProgressBlock
            currentCount={entry.moq_fill_percentage}
            targetCount={100}
            compact
          />
        )}

      {entry.status === "notified" && entry.payment_deadline && (
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span>Kalan süre:</span>
          <CountdownBlock deadline={entry.payment_deadline} compact />
        </div>
      )}

      {/* CTAs */}
      <div className="flex flex-wrap items-center gap-2">
        <PrimaryAction entry={entry} />
        {canRemove && (
          <Button
            variant="ghost"
            size="sm"
            className="text-red-500 hover:text-red-700 hover:bg-red-50 gap-1.5"
            onClick={() => remove(entry.request_id)}
            disabled={isRemoving}
          >
            {isRemoving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Trash2 className="h-3.5 w-3.5" />
            )}
            {isRemoving ? "İptal ediliyor..." : "Listeden Çık"}
          </Button>
        )}
      </div>
    </div>
  );
}

function PrimaryAction({ entry }: { entry: WishlistEntry }) {
  switch (entry.status) {
    case "notified":
      return (
        <Link href={`/payment/${entry.id}`}>
          <Button size="sm" className="gap-1.5 bg-amber-600 hover:bg-amber-700 text-white">
            Ödeme Yap →
          </Button>
        </Link>
      );
    case "paid":
      return (
        <Link href={`/status/${entry.id}`}>
          <Button size="sm" variant="outline" className="gap-1.5">
            Durumu Gör →
          </Button>
        </Link>
      );
    case "expired":
      return (
        <Link href={`/campaigns/${entry.request_id}`}>
          <Button size="sm" variant="outline" className="gap-1.5 text-gray-500">
            Kampanyayı Gör →
          </Button>
        </Link>
      );
    default:
      return (
        <Link href={`/campaigns/${entry.request_id}`}>
          <Button size="sm" variant="outline" className="gap-1.5">
            Kampanyayı Gör →
          </Button>
        </Link>
      );
  }
}
