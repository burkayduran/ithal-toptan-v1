import { Campaign } from "@/features/campaigns/types";
import { formatCurrency } from "@/lib/utils/formatCurrency";
import StatusBadge from "./StatusBadge";
import { Calendar, CheckCircle2 } from "lucide-react";

interface CampaignHeaderProps {
  campaign: Campaign;
}

export default function CampaignHeader({ campaign }: CampaignHeaderProps) {
  const discount = Math.round(
    ((campaign.retailPrice - campaign.groupPrice) / campaign.retailPrice) * 100
  );

  return (
    <div className="space-y-4">
      {/* Category + status */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm text-blue-600 font-medium">{campaign.category}</span>
        <span className="text-gray-300">·</span>
        <StatusBadge status={campaign.status} />
      </div>

      {/* Title */}
      <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 leading-snug">
        {campaign.title}
      </h1>

      {/* Description */}
      <p className="text-gray-600 leading-relaxed">{campaign.description}</p>

      {/* Pricing */}
      <div className="flex items-baseline gap-3">
        <span className="text-3xl font-bold text-gray-900">
          {formatCurrency(campaign.groupPrice)}
        </span>
        <span className="text-lg text-gray-400 line-through">
          {formatCurrency(campaign.retailPrice)}
        </span>
        {discount > 0 && (
          <span className="bg-orange-100 text-orange-700 text-sm font-bold px-2.5 py-0.5 rounded-full">
            %{discount} tasarruf
          </span>
        )}
      </div>

      {/* ETA */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Calendar className="h-4 w-4" />
        {campaign.etaText}
      </div>

      {/* Short specs */}
      {campaign.shortSpecs && campaign.shortSpecs.length > 0 && (
        <ul className="space-y-1.5">
          {campaign.shortSpecs.map((spec, i) => (
            <li key={i} className="flex items-center gap-2 text-sm text-gray-600">
              <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
              {spec}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
