"use client";

import { use } from "react";
import { useProduct, useProducts } from "@/features/campaigns/hooks";
import PageContainer from "@/components/layout/PageContainer";
import CampaignGallery from "@/components/campaign/CampaignGallery";
import CampaignHeader from "@/components/campaign/CampaignHeader";
import JoinPanel from "@/components/campaign/JoinPanel";
import CampaignGrid from "@/components/campaign/CampaignGrid";
import SectionHeader from "@/components/common/SectionHeader";
import LoadingState from "@/components/common/LoadingState";
import ErrorState from "@/components/common/ErrorState";
import { Separator } from "@/components/ui/separator";
import { ChevronRight, Home } from "lucide-react";
import Link from "next/link";

const FAQ_ITEMS = [
  {
    q: "Ne zaman ödeme yapacağım?",
    a: "Ödeme yalnızca hedef sayıya ulaşıldığında talep edilir. MOQ dolmadan ücret alınmaz.",
  },
  {
    q: "MOQ dolmazsa ne olur?",
    a: "Kampanya hedef süresinde dolmazsa kayıt iptal edilir ve herhangi bir ücret alınmaz.",
  },
  {
    q: "Ürünü iade edebilir miyim?",
    a: "Teslimat sonrası ürün koşullara uygunsa iade talebinde bulunabilirsiniz.",
  },
  {
    q: "Teslimat ne kadar sürer?",
    a: "Her kampanya sayfasında tahmini teslimat süresi belirtilmektedir.",
  },
];

export default function CampaignDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: product, isLoading, isError, refetch } = useProduct(id);
  const { data: allProducts } = useProducts();

  const similarProducts = allProducts
    ?.filter((p) => p.id !== id && p.status === "active")
    .slice(0, 3) ?? [];

  if (isLoading) return <LoadingState />;
  if (isError || !product) {
    return (
      <PageContainer>
        <ErrorState
          message="Kampanya bulunamadı veya yüklenirken hata oluştu."
          onRetry={() => refetch()}
        />
      </PageContainer>
    );
  }

  const PLACEHOLDER_IMG =
    "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80";
  const images = product.images?.length > 0 ? product.images : [PLACEHOLDER_IMG];

  return (
    <PageContainer>
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-sm text-gray-500 mb-6">
        <Link href="/" className="flex items-center gap-1 hover:text-gray-700">
          <Home className="h-3.5 w-3.5" />
          Ana Sayfa
        </Link>
        <ChevronRight className="h-3.5 w-3.5" />
        <Link href="/" className="hover:text-gray-700">
          Kampanyalar
        </Link>
        <ChevronRight className="h-3.5 w-3.5" />
        <span className="text-gray-900 font-medium line-clamp-1">{product.title}</span>
      </nav>

      {/* Main layout: gallery + details */}
      <div className="grid lg:grid-cols-2 gap-10 lg:gap-16 mb-16">
        <CampaignGallery images={images} title={product.title} />

        <div className="space-y-6">
          <CampaignHeader product={product} />
          <JoinPanel product={product} />
        </div>
      </div>

      <Separator className="my-10" />

      {/* How it works */}
      <section className="mb-14">
        <SectionHeader title="Nasıl Çalışır?" />
        <ol className="space-y-4">
          {[
            "Bekleme listesine katılın ve adet seçin.",
            "Hedef kişi sayısına ulaşıldığında ödeme bildirimi alırsınız.",
            "Ödemenizi yaptıktan sonra ürün ithal edilir ve teslimat gerçekleşir.",
          ].map((step, i) => (
            <li key={i} className="flex items-start gap-3 text-sm text-gray-700">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-bold text-xs flex items-center justify-center">
                {i + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
      </section>

      {/* FAQ */}
      <section className="mb-14">
        <SectionHeader title="Sık Sorulan Sorular" />
        <div className="space-y-4">
          {FAQ_ITEMS.map((item, i) => (
            <div key={i} className="border border-gray-200 rounded-lg p-4">
              <p className="font-semibold text-gray-900 text-sm">{item.q}</p>
              <p className="mt-1.5 text-sm text-gray-500">{item.a}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Similar campaigns */}
      {similarProducts.length > 0 && (
        <section>
          <SectionHeader title="Benzer Kampanyalar" />
          <CampaignGrid products={similarProducts} />
        </section>
      )}
    </PageContainer>
  );
}
