import Link from "next/link";
import Image from "next/image";
import { Campaign } from "@/features/campaigns/types";
import { formatCurrency } from "@/lib/utils/formatCurrency";
import ProgressBlock from "./ProgressBlock";

interface CampaignCardProps {
  campaign: Campaign;
}

const PLACEHOLDER_IMG = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80";

/** "Hedefe yakın" badge — sadece %70-99 arasında ve hâlâ active durumda */
function NearTargetBadge({ percentage, status }: { percentage: number; status: string }) {
  if (percentage < 70 || percentage >= 100) return null;
  if (status !== "active") return null;
  return (
    <div className="absolute top-3 right-3 bg-orange-50 text-orange-700 text-xs font-semibold px-2.5 py-1 rounded-full border border-orange-200 flex items-center gap-1">
      <span className="h-1.5 w-1.5 rounded-full bg-orange-400 inline-block" />
      Hedefe yakın
    </div>
  );
}

export default function CampaignCard({ campaign }: CampaignCardProps) {
  const thumbnail = campaign.images?.[0] ?? PLACEHOLDER_IMG;
  const canShowProgress =
    campaign.moq != null && campaign.current_participant_count != null;

  const percentage = canShowProgress
    ? Math.min(100, Math.round((campaign.current_participant_count! / campaign.moq!) * 100))
    : 0;

  // CTA: sadece moq_reached durumunda "Talep oluştur" göster
  const showCta = campaign.status === "moq_reached";

  return (
    <div className="group bg-white rounded-2xl overflow-hidden hover:shadow-xl transition-all duration-300 border border-gray-100">
      {/* Image — link olarak sarılı */}
      <Link href={`/campaigns/${campaign.id}`} className="block">
        <div className="relative aspect-square overflow-hidden bg-gray-100">
          <Image
            src={thumbnail}
            alt={campaign.title}
            fill
            className="object-cover group-hover:scale-105 transition-transform duration-500"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />

          {/* "Hedefe yakın" badge */}
          <NearTargetBadge percentage={percentage} status={campaign.status} />
        </div>
      </Link>

      {/* Content */}
      <div className="p-4 space-y-3">
        {/* Title — link */}
        <Link href={`/campaigns/${campaign.id}`}>
          <h3 className="font-semibold text-gray-900 leading-snug line-clamp-2 text-sm group-hover:text-purple-700 transition-colors">
            {campaign.title}
          </h3>
        </Link>

        {/* Price */}
        {campaign.selling_price_try != null ? (
          <div className="flex items-baseline gap-2">
            <span className="text-lg font-bold text-gray-900">
              {formatCurrency(campaign.selling_price_try)}
            </span>
          </div>
        ) : (
          <p className="text-sm text-gray-400 italic">Fiyat yakında</p>
        )}

        {/* Progress */}
        {canShowProgress && (
          <ProgressBlock
            currentCount={campaign.current_participant_count!}
            targetCount={campaign.moq!}
            compact
          />
        )}

        {/* CTA — sadece moq_reached durumunda */}
        {showCta ? (
          <Link href={`/campaigns/${campaign.id}`} className="block">
            <button className="w-full bg-primary hover:bg-primary/90 text-primary-foreground py-2.5 rounded-xl text-sm font-medium transition-colors">
              Talep oluştur
            </button>
          </Link>
        ) : (
          <Link href={`/campaigns/${campaign.id}`} className="block">
            <span className="block w-full text-center text-sm font-medium text-purple-600 hover:text-purple-700 py-2 transition-colors">
              Kampanyayı incele →
            </span>
          </Link>
        )}
      </div>
    </div>
  );
}
