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
import { ArrowRight, Package, ShoppingBag, CreditCard, Zap } from "lucide-react";

export default function HomePage() {
  const { data: campaigns, isLoading, isError, refetch } = useCampaigns();

  const activeCampaigns = campaigns?.filter((p) => p.status === "active") ?? [];
  const moqReachedCampaigns = campaigns?.filter((p) => p.status === "moq_reached") ?? [];
  const paymentCollectingCampaigns = campaigns?.filter((p) => p.status === "payment_collecting") ?? [];

  // Near-unlock: active campaigns where >= 60% of MOQ is filled
  const nearUnlock = activeCampaigns.filter((p) => (p.moq_fill_percentage ?? 0) >= 60);

  // Featured card: priority active → moq_reached → payment_collecting, never internal states
  const featured =
    activeCampaigns[0] ??
    moqReachedCampaigns[0] ??
    paymentCollectingCampaigns[0] ??
    null;

  const hasAnyCampaigns = (campaigns?.length ?? 0) > 0;

  return (
    <>
      {/* Hero */}
      <section className="bg-gradient-to-br from-purple-600 via-indigo-600 to-blue-700 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 bg-white/10 text-white/90 text-sm px-3 py-1.5 rounded-full font-medium">
                <Zap className="h-3.5 w-3.5 text-yellow-300" />
                Grup alımıyla toptan fiyat
              </div>
              <h1 className="text-4xl sm:text-5xl font-extrabold leading-tight">
                Premium Ürünleri
                <br />
                <span className="text-yellow-300">Toptan Fiyatına</span> Alın
              </h1>
              <p className="text-indigo-100 text-lg leading-relaxed max-w-md">
                Yeterli adet bekleme listesine eklendiğinde siparişiniz onaylanır.
                Ödeme yalnızca MOQ dolduğunda alınır.
              </p>
              <a href="#campaigns">
                <Button
                  size="lg"
                  className="bg-white text-purple-700 hover:bg-purple-50 gap-2 font-semibold"
                >
                  Kampanyalara Göz At
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </a>
            </div>

            {featured && (
              <div className="hidden lg:flex justify-end">
                <div className="w-80">
                  <CampaignCard campaign={featured} />
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="bg-gray-50 border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
          <h2 className="text-center text-xl font-bold text-gray-900 mb-10">
            Nasıl Çalışır?
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                icon: <Package className="h-6 w-6 text-purple-600" />,
                step: "1",
                title: "Kampanyayı İnceleyin",
                desc: "Ürün detaylarını, fiyatları ve tahmini teslimat tarihini inceleyin.",
              },
              {
                icon: <ShoppingBag className="h-6 w-6 text-purple-600" />,
                step: "2",
                title: "Bekleme Listesine Katılın",
                desc: "İstediğiniz adedi seçerek bekleme listesine kaydolun.",
              },
              {
                icon: <CreditCard className="h-6 w-6 text-purple-600" />,
                step: "3",
                title: "MOQ Dolunca Ödeyin",
                desc: "Hedef adede ulaşıldığında ödeme bildirimi gelir, siparişiniz onaylanır.",
              },
            ].map((item) => (
              <div key={item.step} className="text-center space-y-3">
                <div className="flex justify-center">
                  <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center">
                    {item.icon}
                  </div>
                </div>
                <div className="text-xs font-bold text-purple-600 uppercase tracking-widest">
                  Adım {item.step}
                </div>
                <h3 className="font-semibold text-gray-900">{item.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Campaign listings */}
      <PageContainer>
        <div id="campaigns">
          {isLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {Array.from({ length: 6 }).map((_, i) => (
                <CampaignCardSkeleton key={i} />
              ))}
            </div>
          ) : isError ? (
            <ErrorState onRetry={() => refetch()} />
          ) : !hasAnyCampaigns ? (
            <EmptyState
              title="Şu an aktif kampanya bulunmuyor"
              description="Yeni kampanyalar için daha sonra tekrar kontrol edin."
            />
          ) : (
            <div className="space-y-14">
              {/* Near unlock – only from active products */}
              {nearUnlock.length > 0 && (
                <section>
                  <SectionHeader
                    title="🔥 Hedefe Yakın"
                    subtitle="Bu kampanyalar hızla dolmak üzere – hemen katılın!"
                  />
                  <CampaignGrid campaigns={nearUnlock} />
                </section>
              )}

              {/* Active campaigns */}
              {activeCampaigns.length > 0 && (
                <section>
                  <SectionHeader
                    title="Aktif Kampanyalar"
                    subtitle="Şu an katılabileceğiniz tüm grup alımları."
                  />
                  <CampaignGrid campaigns={activeCampaigns} />
                </section>
              )}

              {/* MOQ reached – still accepting late joiners */}
              {moqReachedCampaigns.length > 0 && (
                <section>
                  <SectionHeader
                    title="Hedefe Ulaştı"
                    subtitle="Hedef doldu! Katılırsanız ödeme bildirimi alırsınız."
                  />
                  <CampaignGrid campaigns={moqReachedCampaigns} />
                </section>
              )}

              {/* Payment collecting – closed to new joiners */}
              {paymentCollectingCampaigns.length > 0 && (
                <section>
                  <SectionHeader
                    title="Ödeme Aşamasında"
                    subtitle="Bu kampanyalar için ödeme toplanıyor."
                  />
                  <CampaignGrid campaigns={paymentCollectingCampaigns} />
                </section>
              )}
            </div>
          )}
        </div>
      </PageContainer>
    </>
  );
}
