import Link from "next/link";
import Image from "next/image";
import { Campaign } from "@/features/campaigns/types";
import { formatCurrency } from "@/lib/utils/formatCurrency";
import { Button } from "@/components/ui/button";
import StatusBadge from "./StatusBadge";
import ProgressBlock from "./ProgressBlock";
import { ArrowRight, Tag } from "lucide-react";

interface CampaignCardProps {
  campaign: Campaign;
}

export default function CampaignCard({ campaign }: CampaignCardProps) {
  const discount = Math.round(
    ((campaign.retailPrice - campaign.groupPrice) / campaign.retailPrice) * 100
  );

  return (
    <div className="group bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md hover:border-gray-300 transition-all duration-200">
      {/* Image */}
      <div className="relative aspect-[4/3] bg-gray-100 overflow-hidden">
        <Image
          src={campaign.images[0]}
          alt={campaign.title}
          fill
          className="object-cover group-hover:scale-[1.03] transition-transform duration-300"
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
        />
        <div className="absolute top-3 left-3 flex gap-1.5">
          <StatusBadge status={campaign.status} />
        </div>
        {discount > 0 && (
          <div className="absolute top-3 right-3 bg-orange-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
            -%{discount}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4 space-y-3">
        <div>
          <span className="text-xs text-blue-600 font-medium uppercase tracking-wide flex items-center gap-1">
            <Tag className="h-3 w-3" />
            {campaign.category}
          </span>
          <h3 className="mt-1 font-semibold text-gray-900 leading-snug line-clamp-2 text-sm">
            {campaign.title}
          </h3>
        </div>

        {/* Pricing */}
        <div className="flex items-baseline gap-2">
          <span className="text-xl font-bold text-gray-900">
            {formatCurrency(campaign.groupPrice)}
          </span>
          <span className="text-sm text-gray-400 line-through">
            {formatCurrency(campaign.retailPrice)}
          </span>
        </div>

        {/* Progress */}
        <ProgressBlock
          currentCount={campaign.currentCount}
          targetCount={campaign.targetCount}
          compact
        />

        {/* CTA */}
        <Link href={`/campaigns/${campaign.slug}`} className="block">
          <Button
            className="w-full gap-2 text-sm"
            variant={campaign.status === "closed" ? "outline" : "default"}
          >
            {campaign.status === "closed" ? "Detayları Gör" : "Kampanyayı İncele"}
            <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </div>
    </div>
  );
}
