"use client";

import { useProducts } from "@/features/campaigns/hooks";
import { Button } from "@/components/ui/button";
import PageContainer from "@/components/layout/PageContainer";
import SectionHeader from "@/components/common/SectionHeader";
import CampaignGrid from "@/components/campaign/CampaignGrid";
import CampaignCard from "@/components/campaign/CampaignCard";
import LoadingState from "@/components/common/LoadingState";
import ErrorState from "@/components/common/ErrorState";
import EmptyState from "@/components/common/EmptyState";
import { ArrowRight, Package, Users, CreditCard, Zap } from "lucide-react";

export default function HomePage() {
  const { data: products, isLoading, isError, refetch } = useProducts();

  const activeProducts = products?.filter((p) => p.status === "active") ?? [];

  // "Near unlock" = active products where moq_fill_percentage >= 60
  const nearUnlock = activeProducts.filter(
    (p) => (p.moq_fill_percentage ?? 0) >= 60
  );

  const featured = activeProducts[0];

  return (
    <>
      {/* Hero */}
      <section className="bg-gradient-to-br from-blue-600 to-blue-800 text-white">
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
              <p className="text-blue-100 text-lg leading-relaxed max-w-md">
                Yeterli kişi bekleme listesine katıldığında siparişiniz onaylanır.
                Ödeme yalnızca MOQ dolduğunda alınır.
              </p>
              <a href="#campaigns">
                <Button
                  size="lg"
                  className="bg-white text-blue-700 hover:bg-blue-50 gap-2 font-semibold"
                >
                  Kampanyalara Göz At
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </a>
            </div>

            {/* Featured campaign card */}
            {featured && (
              <div className="hidden lg:flex justify-end">
                <div className="w-80">
                  <CampaignCard product={featured} />
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
                icon: <Package className="h-6 w-6 text-blue-600" />,
                step: "1",
                title: "Kampanyayı İnceleyin",
                desc: "Ürün detaylarını, fiyatları ve tahmini teslimat tarihini inceleyin.",
              },
              {
                icon: <Users className="h-6 w-6 text-blue-600" />,
                step: "2",
                title: "Bekleme Listesine Katılın",
                desc: "İstediğiniz adedi seçerek bekleme listesine kaydolun.",
              },
              {
                icon: <CreditCard className="h-6 w-6 text-blue-600" />,
                step: "3",
                title: "MOQ Dolunca Ödeyin",
                desc: "Yeterli kişi katıldığında ödeme bildirimi gelir, siparişiniz onaylanır.",
              },
            ].map((item) => (
              <div key={item.step} className="text-center space-y-3">
                <div className="flex justify-center">
                  <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                    {item.icon}
                  </div>
                </div>
                <div className="text-xs font-bold text-blue-600 uppercase tracking-widest">
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
            <LoadingState />
          ) : isError ? (
            <ErrorState onRetry={() => refetch()} />
          ) : activeProducts.length === 0 ? (
            <EmptyState
              title="Şu an aktif kampanya bulunmuyor"
              description="Yeni kampanyalar için daha sonra tekrar kontrol edin."
            />
          ) : (
            <div className="space-y-14">
              {nearUnlock.length > 0 && (
                <section>
                  <SectionHeader
                    title="🔥 Hedefe Yakın"
                    subtitle="Bu kampanyalar hızla dolmak üzere – hemen katılın!"
                  />
                  <CampaignGrid products={nearUnlock} />
                </section>
              )}

              <section>
                <SectionHeader
                  title="Aktif Kampanyalar"
                  subtitle="Şu an katılabileceğiniz tüm grup alımları."
                />
                <CampaignGrid products={activeProducts} />
              </section>
            </div>
          )}
        </div>
      </PageContainer>
    </>
  );
}
