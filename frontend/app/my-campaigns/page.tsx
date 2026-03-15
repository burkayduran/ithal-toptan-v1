"use client";

import { useEffect } from "react";
import { useAuthStore } from "@/features/auth/store";
import { useWishlist } from "@/features/wishlist/hooks";
import { useMyCampaigns } from "@/features/campaigns/hooks";
import PageContainer from "@/components/layout/PageContainer";
import SectionHeader from "@/components/common/SectionHeader";
import EmptyState from "@/components/common/EmptyState";
import LoadingState from "@/components/common/LoadingState";
import ProgressBlock from "@/components/campaign/ProgressBlock";
import StatusBadge from "@/components/campaign/StatusBadge";
import { formatCurrency } from "@/lib/utils/formatCurrency";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import Image from "next/image";
import { WishlistEntry } from "@/features/wishlist/types";
import { Campaign } from "@/features/campaigns/types";

function MyCampaignRow({
  campaign,
  entry,
}: {
  campaign: Campaign;
  entry: WishlistEntry;
}) {
  const wishlistStatusLabel: Record<WishlistEntry["status"], string> = {
    waiting: "Beklemede",
    notified: "Ödeme Bekleniyor",
    paid: "Ödendi",
    expired: "Süresi Doldu",
  };

  return (
    <div className="flex gap-4 sm:gap-6 bg-white rounded-xl border border-gray-200 p-4 hover:shadow-sm transition-shadow">
      {/* Thumbnail */}
      <div className="relative w-20 h-20 sm:w-24 sm:h-24 rounded-lg overflow-hidden flex-shrink-0 bg-gray-100">
        <Image
          src={campaign.images[0]}
          alt={campaign.title}
          fill
          className="object-cover"
          sizes="96px"
        />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <h3 className="font-semibold text-gray-900 text-sm leading-snug line-clamp-2">
            {campaign.title}
          </h3>
          <StatusBadge status={campaign.status} />
        </div>

        <div className="flex items-center gap-3 text-sm text-gray-600 flex-wrap">
          <span className="font-medium text-gray-900">{formatCurrency(campaign.groupPrice)}</span>
          <span className="text-gray-300">·</span>
          <span>{entry.quantity} adet</span>
          <span className="text-gray-300">·</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 font-medium">
            {wishlistStatusLabel[entry.status]}
          </span>
        </div>

        <ProgressBlock
          currentCount={campaign.currentCount}
          targetCount={campaign.targetCount}
          compact
        />

        <Link href={`/campaigns/${campaign.slug}`}>
          <Button variant="outline" size="sm" className="mt-1">
            Kampanyayı Gör →
          </Button>
        </Link>
      </div>
    </div>
  );
}

export default function MyCampaignsPage() {
  const { user, hydrate, openAuthModal } = useAuthStore();
  const { data: wishlist, isLoading: wishlistLoading } = useWishlist();

  const wishlistIds = wishlist?.map((w) => w.requestId) ?? [];
  const { data: campaigns, isLoading: campaignsLoading } = useMyCampaigns(wishlistIds);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  // Prompt unauthenticated users to login
  useEffect(() => {
    if (!user && !wishlistLoading) {
      openAuthModal();
    }
  }, [user, wishlistLoading, openAuthModal]);

  const isLoading = wishlistLoading || campaignsLoading;

  // Merge campaigns with their wishlist entries
  const items =
    wishlist?.map((entry) => ({
      entry,
      campaign: campaigns?.find((c) => c.id === entry.requestId),
    })).filter((item) => !!item.campaign) ?? [];

  return (
    <PageContainer>
      <SectionHeader
        title="Siparişlerim"
        subtitle="Katıldığınız kampanyalar ve bekleme listesi durumları."
      />

      {!user ? (
        <EmptyState
          title="Giriş yapmalısınız"
          description="Siparişlerinizi görmek için lütfen giriş yapın."
        />
      ) : isLoading ? (
        <LoadingState />
      ) : items.length === 0 ? (
        <EmptyState
          title="Henüz kampanyaya katılmadınız"
          description="Aktif kampanyalara göz atarak bekleme listesine katılabilirsiniz."
          actionLabel="Kampanyaları İncele"
          actionHref="/"
        />
      ) : (
        <div className="space-y-4">
          {items.map(({ entry, campaign }) => (
            <MyCampaignRow key={entry.id} campaign={campaign!} entry={entry} />
          ))}
        </div>
      )}
    </PageContainer>
  );
}
