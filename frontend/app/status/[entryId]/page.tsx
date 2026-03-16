"use client";

import { use } from "react";
import Link from "next/link";
import Image from "next/image";
import { useStatusEntry } from "@/features/payments/hooks";
import type { WishlistStatus } from "@/features/wishlist/types";
import PageContainer from "@/components/layout/PageContainer";
import LoadingState from "@/components/common/LoadingState";
import ErrorState from "@/components/common/ErrorState";
import ConfirmationHeader from "@/components/status/ConfirmationHeader";
import DeliveryEstimateCard from "@/components/status/DeliveryEstimateCard";
import SupportBlock from "@/components/status/SupportBlock";
import TimelineStepper from "@/components/campaign/TimelineStepper";
import StateNoticeBanner from "@/components/campaign/StateNoticeBanner";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ChevronRight, Home } from "lucide-react";

const PLACEHOLDER_IMG =
  "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80";

export default function StatusPage({
  params,
}: {
  params: Promise<{ entryId: string }>;
}) {
  const { entryId } = use(params);
  const { data: entry, isLoading, isError, refetch } = useStatusEntry(entryId);

  if (isLoading) return <LoadingState />;
  if (isError || !entry) {
    return (
      <PageContainer>
        <ErrorState
          message="Durum bilgisi bulunamadı."
          onRetry={() => refetch()}
        />
      </PageContainer>
    );
  }

  const thumbnail = entry.product_image ?? PLACEHOLDER_IMG;
  const entryStatus = entry.status as WishlistStatus;

  return (
    <PageContainer>
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-sm text-gray-500 mb-6">
        <Link href="/" className="flex items-center gap-1 hover:text-gray-700">
          <Home className="h-3.5 w-3.5" />
          Ana Sayfa
        </Link>
        <ChevronRight className="h-3.5 w-3.5" />
        <Link href="/my-campaigns" className="hover:text-gray-700">
          Siparişlerim
        </Link>
        <ChevronRight className="h-3.5 w-3.5" />
        <span className="text-gray-900 font-medium">Sipariş Durumu</span>
      </nav>

      <div className="max-w-2xl mx-auto space-y-6">
        {/* Product thumbnail + confirmation header */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-5">
          <div className="flex items-center gap-4">
            <div className="relative w-20 h-20 rounded-lg overflow-hidden flex-shrink-0 bg-gray-100">
              <Image
                src={thumbnail}
                alt={entry.product_title}
                fill
                className="object-cover"
                sizes="80px"
              />
            </div>
            <ConfirmationHeader
              entryStatus={entryStatus}
              productTitle={entry.product_title}
            />
          </div>

          {/* Expired recovery banner */}
          {entryStatus === "expired" && (
            <StateNoticeBanner
              type="warning"
              message="Ödeme pencereniz kapandı. Kampanya sıfırlanırsa bekleme listesine tekrar katılabilirsiniz."
            />
          )}

          {/* Waiting / not paid yet — navigate to payment */}
          {entryStatus === "notified" && (
            <>
              <StateNoticeBanner
                type="warning"
                title="Ödeme bekleniyor"
                message="Yerinizi onaylamak için ödemeyi tamamlayın."
              />
              <Link href={`/payment/${entry.id}`}>
                <Button className="w-full bg-amber-600 hover:bg-amber-700">
                  Ödemeye Git →
                </Button>
              </Link>
            </>
          )}
        </div>

        {/* Timeline */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-900 text-sm mb-5">Sipariş Aşamaları</h2>
          <TimelineStepper currentStage={entry.stage} />
        </div>

        {/* Delivery estimate — only relevant for paid/shipped */}
        {(entryStatus === "paid") && entry.lead_time_days && (
          <DeliveryEstimateCard leadTimeDays={entry.lead_time_days} />
        )}

        <Separator />

        {/* CTAs */}
        <div className="flex flex-wrap gap-3">
          <Link href="/my-campaigns">
            <Button variant="outline" size="sm">
              ← Siparişlerime Dön
            </Button>
          </Link>
          <Link href={`/campaigns/${entry.request_id}`}>
            <Button variant="ghost" size="sm" className="text-gray-500">
              Kampanyayı Gör
            </Button>
          </Link>
        </div>

        {/* Support */}
        <SupportBlock />
      </div>
    </PageContainer>
  );
}
