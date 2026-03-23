import { Campaign } from "@/features/campaigns/types";
import CampaignCard from "./CampaignCard";

interface CampaignGridProps {
  campaigns: Campaign[];
}

export default function CampaignGrid({ campaigns }: CampaignGridProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {campaigns.map((campaign) => (
        <CampaignCard key={campaign.id} campaign={campaign} />
      ))}
    </div>
  );
}
