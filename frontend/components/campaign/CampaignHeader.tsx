import { Product } from "@/features/campaigns/types";
import { formatCurrency } from "@/lib/utils/formatCurrency";
import StatusBadge from "./StatusBadge";
import { Clock } from "lucide-react";

interface CampaignHeaderProps {
  product: Product;
}

export default function CampaignHeader({ product }: CampaignHeaderProps) {
  return (
    <div className="space-y-4">
      {/* Status */}
      <div className="flex items-center gap-2 flex-wrap">
        <StatusBadge status={product.status} />
      </div>

      {/* Title */}
      <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 leading-snug">
        {product.title}
      </h1>

      {/* Description */}
      {product.description && (
        <p className="text-gray-600 leading-relaxed">{product.description}</p>
      )}

      {/* Price – no retailPrice from backend, show group price only */}
      {product.selling_price_try != null ? (
        <div className="flex items-baseline gap-3">
          <span className="text-3xl font-bold text-gray-900">
            {formatCurrency(product.selling_price_try)}
          </span>
          <span className="text-sm text-gray-400">/ adet (grup fiyatı)</span>
        </div>
      ) : (
        <p className="text-lg text-gray-400 italic">Fiyat yakında açıklanacak</p>
      )}

      {/* Lead time */}
      {product.lead_time_days != null && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Clock className="h-4 w-4" />
          Tahmini teslimat: ~{product.lead_time_days} gün
        </div>
      )}
    </div>
  );
}
