"use client";

import { use } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePaymentEntry } from "@/features/payments/hooks";
import PageContainer from "@/components/layout/PageContainer";
import LoadingState from "@/components/common/LoadingState";
import ErrorState from "@/components/common/ErrorState";
import CountdownBlock from "@/components/campaign/CountdownBlock";
import StateNoticeBanner from "@/components/campaign/StateNoticeBanner";
import PaymentPanel from "@/components/campaign/PaymentPanel";
import PaymentSummaryCard from "@/components/payment/PaymentSummaryCard";
import SupportBlock from "@/components/status/SupportBlock";
import { ChevronRight, Home } from "lucide-react";

const PLACEHOLDER_IMG =
  "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80";

export default function PaymentPage({
  params,
}: {
  params: Promise<{ participantId: string }>;
}) {
  const { participantId } = use(params);
  const { data: entry, isLoading, isError, refetch } = usePaymentEntry(participantId);

  if (isLoading) return <LoadingState />;
  if (isError || !entry) {
    return (
      <PageContainer>
        <ErrorState
          message="Ödeme kaydı bulunamadı."
          onRetry={() => refetch()}
        />
      </PageContainer>
    );
  }

  const isDeadlinePassed =
    !!entry.payment_deadline && new Date(entry.payment_deadline) < new Date();
  const isExpired = entry.status === "expired" || isDeadlinePassed;
  const isPaid = entry.status === "paid";
  const thumbnail = entry.campaign_image ?? PLACEHOLDER_IMG;
  const pricePerUnit =
    entry.quantity > 0 ? entry.total_amount / entry.quantity : entry.total_amount;

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
        <span className="text-gray-900 font-medium">Ödeme</span>
      </nav>

      <div className="max-w-2xl mx-auto space-y-6">
        {/* Expired / paid banners */}
        {isExpired && (
          <StateNoticeBanner
            type="error"
            title="Ödeme süresi doldu"
            message="Maalesef ödeme pencereniz kapandı. Bir sonraki grup alımında tekrar katılabilirsiniz."
          />
        )}
        {isPaid && (
          <StateNoticeBanner
            type="success"
            title="Ödeme tamamlandı"
            message="Ödemeniz alındı. Sipariş durumunuzu takip etmek için aşağıdaki bağlantıya tıklayın."
          />
        )}

        {/* Product hero */}
        <div className="flex items-center gap-4 bg-white rounded-xl border border-gray-200 p-4">
          <div className="relative w-20 h-20 rounded-lg overflow-hidden flex-shrink-0 bg-gray-100">
            <Image
              src={thumbnail}
              alt={entry.campaign_title}
              fill
              className="object-cover"
              sizes="80px"
            />
          </div>
          <div>
            <h1 className="font-bold text-gray-900 text-base leading-snug line-clamp-2">
              {entry.campaign_title}
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">{entry.quantity} adet</p>
          </div>
        </div>

        {/* Countdown — only for active notified entries */}
        {!isExpired && !isPaid && entry.payment_deadline && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-700">Ödeme için kalan süre</p>
            <CountdownBlock deadline={entry.payment_deadline} />
            <p className="text-xs text-gray-400">
              Süre dolmadan ödemenizi tamamlamayı unutmayın.
            </p>
          </div>
        )}

        {/* Summary */}
        <PaymentSummaryCard
          productTitle={entry.campaign_title}
          quantity={entry.quantity}
          pricePerUnit={pricePerUnit}
          totalAmount={entry.total_amount}
        />

        {/* Payment CTA */}
        <PaymentPanel
          participantId={entry.id}
          totalAmount={entry.total_amount}
          isExpired={isExpired}
          isPaid={isPaid}
        />

        {/* What your payment does */}
        {!isExpired && !isPaid && (
          <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
            <p className="text-xs text-gray-500 leading-relaxed">
              <strong className="text-gray-700">Ödemeniz ne anlama gelir?</strong>{" "}
              Ödemenizi tamamlamanız, grup alımındaki yerinizi garanti altına alır.
              Yeterli katılımcı sağlandığında ürün tedarikçiden sipariş edilir ve
              kargoya verilir.
            </p>
          </div>
        )}

        {/* Support */}
        <SupportBlock />
      </div>
    </PageContainer>
  );
}
