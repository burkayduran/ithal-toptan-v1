"use client";

import { useEffect } from "react";
import { useAuthStore } from "@/features/auth/store";
import { useMyCampaigns } from "@/features/payments/hooks";
import PageContainer from "@/components/layout/PageContainer";
import SectionHeader from "@/components/common/SectionHeader";
import EmptyState from "@/components/common/EmptyState";
import LoadingState from "@/components/common/LoadingState";
import MyCampaignTabs from "@/components/wishlist/MyCampaignTabs";

export default function MyCampaignsPage() {
  const { user, isHydrated, openAuthModal } = useAuthStore();
  const { data: campaigns, isLoading } = useMyCampaigns();

  useEffect(() => {
    if (isHydrated && !user) {
      openAuthModal();
    }
  }, [isHydrated, user, openAuthModal]);

  return (
    <PageContainer>
      <SectionHeader
        title="Siparişlerim"
        subtitle="Katıldığınız kampanyalar ve ödeme durumları."
      />

      {!isHydrated || isLoading ? (
        <LoadingState />
      ) : !user ? (
        <EmptyState
          title="Giriş yapmalısınız"
          description="Siparişlerinizi görmek için lütfen giriş yapın."
        />
      ) : !campaigns || campaigns.length === 0 ? (
        <EmptyState
          title="Henüz kampanyaya katılmadınız"
          description="Aktif kampanyalara göz atarak bekleme listesine katılabilirsiniz."
          actionLabel="Kampanyaları İncele"
          actionHref="/"
        />
      ) : (
        <MyCampaignTabs entries={campaigns} />
      )}
    </PageContainer>
  );
}
