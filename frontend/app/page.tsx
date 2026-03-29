"use client";

import { useCampaigns } from "@/features/campaigns/hooks";
import { Button } from "@/components/ui/button";
import PageContainer from "@/components/layout/PageContainer";
import SectionHeader from "@/components/common/SectionHeader";
import CampaignGrid from "@/components/campaign/CampaignGrid";
import CampaignCard from "@/components/campaign/CampaignCard";
import CampaignCardSkeleton from "@/components/campaign/CampaignCardSkeleton";
import ErrorState from "@/components/common/ErrorState";
import EmptyState from "@/components/common/EmptyState";
import {
  ArrowRight,
  Heart,
  Users,
  Bell,
  ShoppingBag,
  Sparkles,
  TrendingUp,
  CreditCard,
} from "lucide-react";
import { isCampaignReached } from "@/lib/utils/campaign";

export default function HomePage() {
  const { data: campaigns, isLoading, isError, refetch } = useCampaigns();

  const activeCampaigns =
    campaigns?.filter((p) => p.status === "active") ?? [];
  const moqReachedCampaigns =
    campaigns?.filter((p) => p.status === "moq_reached" && isCampaignReached(p)) ?? [];
  const paymentCollectingCampaigns =
    campaigns?.filter((p) => p.status === "payment_collecting") ?? [];

  const nearUnlock = activeCampaigns.filter(
    (p) => (p.moq_fill_percentage ?? 0) >= 60
  );

  const featured =
    activeCampaigns[0] ??
    moqReachedCampaigns[0] ??
    paymentCollectingCampaigns[0] ??
    null;

  const hasAnyCampaigns = (campaigns?.length ?? 0) > 0;

  return (
    <div className="min-h-screen">
      {/* ════════════════════════════════════════
          HERO SECTION — Gradient + wave bottom
         ════════════════════════════════════════ */}
      <section className="relative bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 text-white overflow-hidden">
        {/* Subtle pattern overlay */}
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wOCI+PHBhdGggZD0iTTM2IDM0YzAtMiAyLTQgMi00czIgMiAyIDQtMiA0LTIgNC0yLTItMi00eiIvPjwvZz48L2c+PC9zdmc+')] opacity-30" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28 relative">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left — text */}
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 bg-white/20 backdrop-blur-sm text-white/90 text-sm px-4 py-2 rounded-full font-medium">
                <Sparkles className="h-4 w-4 text-yellow-300" />
                Grup alımıyla toptan fiyat
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight">
                Premium Ürünleri
                <br />
                <span className="text-yellow-300">Toptan Fiyatına</span> Alın
              </h1>

              <p className="text-indigo-100 text-lg leading-relaxed max-w-md">
                Bekleme listesine ekleyin, yeterli adet dolduğunda herkes
                toptan fiyatından alsın. Ödeme yalnızca MOQ dolduğunda alınır.
              </p>

              <div className="flex flex-col sm:flex-row gap-4">
                <a href="#campaigns">
                  <Button
                    size="lg"
                    className="bg-white text-indigo-600 hover:bg-indigo-50 gap-2 font-semibold shadow-xl hover:shadow-2xl"
                  >
                    Kampanyalara Göz At
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </a>
              </div>
            </div>

            {/* Right — featured card */}
            {featured && (
              <div className="hidden lg:flex justify-end">
                <div className="w-80 animate-float">
                  <CampaignCard campaign={featured} />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Wave SVG — smooth transition to next section */}
        <div className="absolute bottom-0 left-0 right-0">
          <svg
            viewBox="0 0 1440 120"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M0 120L60 105C120 90 240 60 360 45C480 30 600 30 720 37.5C840 45 960 60 1080 67.5C1200 75 1320 75 1380 75L1440 75V120H1380C1320 120 1200 120 1080 120C960 120 840 120 720 120C600 120 480 120 360 120C240 120 120 120 60 120H0Z"
              fill="white"
            />
          </svg>
        </div>
      </section>

      {/* ════════════════════════════════════════
          HOW IT WORKS — 4 steps with gradient icons
         ════════════════════════════════════════ */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Nasıl Çalışır?
            </h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Grup alım sistemimiz ile en iyi fiyatları yakalayın
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              {
                icon: Heart,
                title: "Kampanyayı İnceleyin",
                desc: "İlginizi çeken ürünleri keşfedin ve detaylarını inceleyin",
                color: "from-pink-500 to-rose-500",
              },
              {
                icon: Users,
                title: "Listeye Katılın",
                desc: "İstediğiniz adedi seçerek bekleme listesine kaydolun",
                color: "from-blue-500 to-indigo-500",
              },
              {
                icon: Bell,
                title: "Bildirim Alın",
                desc: "MOQ dolduğunda anında bildirim alırsınız",
                color: "from-yellow-500 to-orange-500",
              },
              {
                icon: CreditCard,
                title: "Toptan Fiyata Alın",
                desc: "Hedef dolunca ödeme yapın, siparişiniz onaylansın",
                color: "from-green-500 to-emerald-500",
              },
            ].map((step, i) => (
              <div key={i} className="text-center">
                <div
                  className={`w-14 h-14 mx-auto mb-4 rounded-2xl bg-gradient-to-br ${step.color} flex items-center justify-center shadow-lg`}
                >
                  <step.icon className="w-7 h-7 text-white" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  {step.title}
                </h3>
                <p className="text-gray-600 text-sm">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════
          CAMPAIGN SECTIONS
         ════════════════════════════════════════ */}
      <div id="campaigns">
        {isLoading ? (
          <PageContainer>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {Array.from({ length: 8 }).map((_, i) => (
                <CampaignCardSkeleton key={i} />
              ))}
            </div>
          </PageContainer>
        ) : isError ? (
          <PageContainer>
            <ErrorState onRetry={() => refetch()} />
          </PageContainer>
        ) : !hasAnyCampaigns ? (
          <PageContainer>
            <EmptyState
              title="Şu an aktif kampanya bulunmuyor"
              description="Yeni kampanyalar için daha sonra tekrar kontrol edin."
            />
          </PageContainer>
        ) : (
          <>
            {/* ── MOQ Reached — green pastel bg ── */}
            {moqReachedCampaigns.length > 0 && (
              <section className="py-16 bg-gradient-to-br from-green-50 to-emerald-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                  <SectionHeader
                    title="Hedefe Ulaştı!"
                    subtitle="Bu kampanyalar doldu — hemen talep oluşturun!"
                    icon={ShoppingBag}
                    iconColor="bg-green-500"
                  />
                  <CampaignGrid campaigns={moqReachedCampaigns} />
                </div>
              </section>
            )}

            {/* ── Near Unlock — orange pastel bg ── */}
            {nearUnlock.length > 0 && (
              <section className="py-16 bg-gradient-to-br from-orange-50 to-yellow-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                  <SectionHeader
                    title="Hedefe Yakın!"
                    subtitle="Bu kampanyalar dolmak üzere — hemen katılın!"
                    icon={TrendingUp}
                    iconColor="bg-orange-500"
                  />
                  <CampaignGrid campaigns={nearUnlock} />
                </div>
              </section>
            )}

            {/* ── Active — neutral bg ── */}
            {activeCampaigns.length > 0 && (
              <section className="py-16 bg-gray-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                  <SectionHeader
                    title="Aktif Kampanyalar"
                    subtitle="Şu an katılabileceğiniz tüm grup alımları"
                    icon={Heart}
                    iconColor="bg-indigo-500"
                  />
                  <CampaignGrid campaigns={activeCampaigns} />
                </div>
              </section>
            )}

            {/* ── Payment Collecting ── */}
            {paymentCollectingCampaigns.length > 0 && (
              <section className="py-16 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                  <SectionHeader
                    title="Ödeme Aşamasında"
                    subtitle="Bu kampanyalar için ödeme toplanıyor"
                    icon={CreditCard}
                    iconColor="bg-amber-500"
                  />
                  <CampaignGrid campaigns={paymentCollectingCampaigns} />
                </div>
              </section>
            )}
          </>
        )}
      </div>

      {/* ════════════════════════════════════════
          CTA SECTION — bottom gradient
         ════════════════════════════════════════ */}
      <section className="py-20 bg-gradient-to-r from-indigo-600 to-purple-600 text-white">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-4">Tasarruf Etmeye Hazır Mısınız?</h2>
          <p className="text-indigo-100 mb-8 text-lg">
            Binlerce akıllı alıcıya katılın — birlikte alın, birlikte kazanın.
          </p>
          <a href="#campaigns">
            <Button
              size="lg"
              className="bg-white text-indigo-600 hover:bg-indigo-50 gap-2 font-semibold shadow-xl"
            >
              Kampanyaları Keşfet
              <ArrowRight className="w-5 h-5" />
            </Button>
          </a>
        </div>
      </section>
    </div>
  );
}
