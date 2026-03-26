import Link from "next/link";
import Image from "next/image";
import { Sparkles, TrendingUp } from "lucide-react";
import { Campaign } from "@/features/campaigns/types";
import { formatCurrency } from "@/lib/utils/formatCurrency";
import ProgressBlock from "./ProgressBlock";

interface CampaignCardProps {
  campaign: Campaign;
}

const PLACEHOLDER_IMG =
  "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80";

export default function CampaignCard({ campaign }: CampaignCardProps) {
  const thumbnail = campaign.images?.[0] ?? PLACEHOLDER_IMG;
  const canShowProgress =
    campaign.moq != null && campaign.current_participant_count != null;

  const percentage = canShowProgress
    ? Math.min(
        100,
        Math.round(
          (campaign.current_participant_count! / campaign.moq!) * 100
        )
      )
    : 0;

  const isReached = percentage >= 100;
  const isNearTarget = percentage >= 70 && percentage < 100;
  const showCta = campaign.status === "moq_reached";

  return (
    <Link
      href={`/campaigns/${campaign.id}`}
      className="group bg-white rounded-2xl shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden border border-gray-100 flex flex-col"
    >
      {/* ── Image ── */}
      <div className="relative aspect-square overflow-hidden bg-gray-100">
        <Image
          src={thumbnail}
          alt={campaign.title}
          fill
          className="object-cover group-hover:scale-105 transition-transform duration-500"
          sizes="(max-width:768px) 100vw,(max-width:1200px) 50vw,25vw"
        />

        {/* Near-target badge — top-left, orange gradient */}
        {isNearTarget && campaign.status === "active" && (
          <div className="absolute top-3 left-3 bg-gradient-to-r from-yellow-400 to-orange-500 text-white text-xs font-bold px-2.5 py-1 rounded-full flex items-center gap-1 shadow-md animate-pulse-glow">
            <TrendingUp className="w-3 h-3" />
            Hedefe Yakın!
          </div>
        )}

        {/* MOQ reached badge — top-right, green gradient */}
        {isReached && (
          <div className="absolute top-3 right-3 bg-gradient-to-r from-green-400 to-emerald-500 text-white text-xs font-bold px-2.5 py-1 rounded-full flex items-center gap-1 shadow-md">
            <Sparkles className="w-3 h-3" />
            Hazır!
          </div>
        )}
      </div>

      {/* ── Content ── */}
      <div className="p-4 space-y-3 flex-1 flex flex-col">
        {/* Status pill */}
        {campaign.status === "active" && (
          <span className="self-start text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-1 rounded-full">
            Aktif Kampanya
          </span>
        )}
        {campaign.status === "payment_collecting" && (
          <span className="self-start text-xs font-medium text-amber-700 bg-amber-50 px-2 py-1 rounded-full">
            Ödeme Aşaması
          </span>
        )}

        {/* Title */}
        <h3 className="font-semibold text-gray-900 leading-snug line-clamp-2 text-sm group-hover:text-indigo-600 transition-colors">
          {campaign.title}
        </h3>

        {/* Price */}
        {campaign.selling_price_try != null ? (
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold text-gray-900">
              {formatCurrency(campaign.selling_price_try)}
            </span>
          </div>
        ) : (
          <p className="text-sm text-gray-400 italic">Fiyat yakında</p>
        )}

        {/* Progress — pushed to bottom */}
        <div className="mt-auto pt-1">
          {canShowProgress && (
            <ProgressBlock
              currentCount={campaign.current_participant_count!}
              targetCount={campaign.moq!}
              compact
            />
          )}
        </div>

        {/* CTA */}
        {showCta ? (
          <button className="w-full bg-gradient-to-r from-green-500 to-emerald-600 text-white py-2.5 rounded-xl text-sm font-medium hover:from-green-600 hover:to-emerald-700 transition-all flex items-center justify-center gap-2 shadow-sm">
            <Sparkles className="w-4 h-4" />
            Talep Oluştur
          </button>
        ) : (
          <span className="block w-full text-center text-sm font-medium text-indigo-600 hover:text-indigo-700 py-2 transition-colors">
            Kampanyayı İncele →
          </span>
        )}
      </div>
    </Link>
  );
}
