import { Product } from "@/features/campaigns/types";
import CampaignCard from "./CampaignCard";

interface CampaignGridProps {
  products: Product[];
}

export default function CampaignGrid({ products }: CampaignGridProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      {products.map((product) => (
        <CampaignCard key={product.id} product={product} />
      ))}
    </div>
  );
}
