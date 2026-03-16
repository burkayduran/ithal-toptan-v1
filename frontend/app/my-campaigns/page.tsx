"use client";

import { useEffect } from "react";
import { useAuthStore } from "@/features/auth/store";
import { useWishlist, useRemoveFromWishlist } from "@/features/wishlist/hooks";
import { WishlistEntry } from "@/features/wishlist/types";
import PageContainer from "@/components/layout/PageContainer";
import SectionHeader from "@/components/common/SectionHeader";
import EmptyState from "@/components/common/EmptyState";
import LoadingState from "@/components/common/LoadingState";
import { formatCurrency } from "@/lib/utils/formatCurrency";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import Image from "next/image";
import { Loader2, Trash2 } from "lucide-react";

const WISHLIST_STATUS_LABEL: Record<WishlistEntry["status"], string> = {
  waiting: "Beklemede",
  notified: "Ödeme Bekleniyor",
  paid: "Ödendi",
  expired: "Süresi Doldu",
  cancelled: "İptal",
};

const PLACEHOLDER_IMG =
  "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80";

// Only these statuses allow removal (matches backend logic)
const REMOVABLE_STATUSES: WishlistEntry["status"][] = ["waiting", "expired"];

function WishlistRow({ entry }: { entry: WishlistEntry }) {
  const thumbnail = entry.product_image ?? PLACEHOLDER_IMG;
  const title = entry.product_title ?? "Ürün";
  const canRemove = REMOVABLE_STATUSES.includes(entry.status);
  const { mutate: remove, isPending: isRemoving, error: removeError } = useRemoveFromWishlist();

  return (
    <div className="flex gap-4 sm:gap-6 bg-white rounded-xl border border-gray-200 p-4 hover:shadow-sm transition-shadow">
      {/* Thumbnail */}
      <div className="relative w-20 h-20 sm:w-24 sm:h-24 rounded-lg overflow-hidden flex-shrink-0 bg-gray-100">
        <Image
          src={thumbnail}
          alt={title}
          fill
          className="object-cover"
          sizes="96px"
        />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <h3 className="font-semibold text-gray-900 text-sm leading-snug line-clamp-2">
            {title}
          </h3>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border bg-gray-100 text-gray-600 border-gray-200 whitespace-nowrap">
            {WISHLIST_STATUS_LABEL[entry.status]}
          </span>
        </div>

        <div className="flex items-center gap-3 text-sm text-gray-600 flex-wrap">
          {entry.selling_price_try != null && (
            <>
              <span className="font-medium text-gray-900">
                {formatCurrency(entry.selling_price_try)}
              </span>
              <span className="text-gray-300">·</span>
            </>
          )}
          <span>{entry.quantity} adet</span>
          {entry.payment_deadline && (
            <>
              <span className="text-gray-300">·</span>
              <span className="text-xs text-orange-600">
                Son ödeme: {new Date(entry.payment_deadline).toLocaleDateString("tr-TR")}
              </span>
            </>
          )}
        </div>

        {removeError && (
          <p className="text-xs text-red-600">
            {(removeError as Error).message || "Bir hata oluştu."}
          </p>
        )}

        <div className="flex items-center gap-2 flex-wrap mt-1">
          <Link href={`/campaigns/${entry.request_id}`}>
            <Button variant="outline" size="sm">
              Kampanyayı Gör →
            </Button>
          </Link>

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
    </div>
  );
}

export default function MyCampaignsPage() {
  const { user, isHydrated, openAuthModal } = useAuthStore();
  const { data: wishlist, isLoading } = useWishlist();

  useEffect(() => {
    if (isHydrated && !user) {
      openAuthModal();
    }
  }, [isHydrated, user, openAuthModal]);

  return (
    <PageContainer>
      <SectionHeader
        title="Siparişlerim"
        subtitle="Katıldığınız kampanyalar ve bekleme listesi durumları."
      />

      {!isHydrated || isLoading ? (
        <LoadingState />
      ) : !user ? (
        <EmptyState
          title="Giriş yapmalısınız"
          description="Siparişlerinizi görmek için lütfen giriş yapın."
        />
      ) : !wishlist || wishlist.length === 0 ? (
        <EmptyState
          title="Henüz kampanyaya katılmadınız"
          description="Aktif kampanyalara göz atarak bekleme listesine katılabilirsiniz."
          actionLabel="Kampanyaları İncele"
          actionHref="/"
        />
      ) : (
        <div className="space-y-4">
          {wishlist.map((entry) => (
            <WishlistRow key={entry.id} entry={entry} />
          ))}
        </div>
      )}
    </PageContainer>
  );
}
