"use client";

import { use } from "react";
import { useProduct, useSimilarProducts } from "@/features/campaigns/hooks";
import { useWishlist } from "@/features/wishlist/hooks";
import PageContainer from "@/components/layout/PageContainer";
import CampaignGallery from "@/components/campaign/CampaignGallery";
import CampaignHeader from "@/components/campaign/CampaignHeader";
import JoinPanel from "@/components/campaign/JoinPanel";
import CampaignGrid from "@/components/campaign/CampaignGrid";
import SectionHeader from "@/components/common/SectionHeader";
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
  const { data: similarProducts = [] } = useSimilarProducts(id);
  const { data: wishlist } = useWishlist();
  const myEntry = wishlist?.find((e) => e.request_id === id) ?? null;

  if (isLoading) {
    return (
      <PageContainer>
        <div className="animate-pulse space-y-6">
          {/* Breadcrumb skeleton */}
          <div className="flex gap-2 items-center">
            <div className="h-4 bg-gray-200 rounded w-16" />
            <div className="h-4 bg-gray-200 rounded w-4" />
            <div className="h-4 bg-gray-200 rounded w-20" />
            <div className="h-4 bg-gray-200 rounded w-4" />
            <div className="h-4 bg-gray-200 rounded w-32" />
          </div>
          {/* Main grid skeleton */}
          <div className="grid lg:grid-cols-2 gap-10 lg:gap-16">
            <div className="aspect-square bg-gray-200 rounded-xl" />
            <div className="space-y-4 pt-2">
              <div className="h-7 bg-gray-200 rounded w-3/4" />
              <div className="h-5 bg-gray-200 rounded w-1/3" />
              <div className="h-4 bg-gray-200 rounded w-1/4" />
              <div className="space-y-2 mt-6">
                <div className="h-3 bg-gray-200 rounded w-full" />
                <div className="h-3 bg-gray-200 rounded w-5/6" />
              </div>
              <div className="h-36 bg-gray-200 rounded-xl mt-4" />
            </div>
          </div>
        </div>
      </PageContainer>
    );
  }
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
        <Link href="/campaigns" className="hover:text-gray-700">
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
          <JoinPanel product={product} entry={myEntry} />
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
