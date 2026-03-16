import Link from "next/link";
import Image from "next/image";
import { Product } from "@/features/campaigns/types";
import { formatCurrency } from "@/lib/utils/formatCurrency";
import { Button } from "@/components/ui/button";
import StatusBadge from "./StatusBadge";
import ProgressBlock from "./ProgressBlock";
import { ArrowRight } from "lucide-react";

interface CampaignCardProps {
  product: Product;
}

const PLACEHOLDER_IMG = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80";

export default function CampaignCard({ product }: CampaignCardProps) {
  const thumbnail = product.images?.[0] ?? PLACEHOLDER_IMG;
  const canShowProgress =
    product.moq != null && product.current_wishlist_count != null;

  return (
    <div className="group bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md hover:border-gray-300 transition-all duration-200">
      {/* Image */}
      <div className="relative aspect-[4/3] bg-gray-100 overflow-hidden">
        <Image
          src={thumbnail}
          alt={product.title}
          fill
          className="object-cover group-hover:scale-[1.03] transition-transform duration-300"
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
        />
        <div className="absolute top-3 left-3">
          <StatusBadge status={product.status} />
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-3">
        <h3 className="font-semibold text-gray-900 leading-snug line-clamp-2 text-sm">
          {product.title}
        </h3>

        {/* Price */}
        {product.selling_price_try != null ? (
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold text-gray-900">
              {formatCurrency(product.selling_price_try)}
            </span>
            <span className="text-xs text-gray-400">/ adet</span>
          </div>
        ) : (
          <p className="text-sm text-gray-400 italic">Fiyat yakında</p>
        )}

        {/* Progress */}
        {canShowProgress && (
          <ProgressBlock
            currentCount={product.current_wishlist_count!}
            targetCount={product.moq!}
            compact
          />
        )}

        {/* CTA */}
        <Link href={`/campaigns/${product.id}`} className="block">
          <Button
            className="w-full gap-2 text-sm"
            variant={
              product.status === "cancelled" || product.status === "delivered"
                ? "outline"
                : "default"
            }
          >
            Kampanyayı İncele
            <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </div>
    </div>
  );
}
