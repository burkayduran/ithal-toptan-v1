import { Badge } from "@/components/ui/badge";
import { CampaignStatus } from "@/features/campaigns/types";
import { getStatusLabel } from "@/lib/utils/getStatusLabel";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: CampaignStatus;
  className?: string;
}

const statusStyles: Record<CampaignStatus, string> = {
  active: "bg-green-100 text-green-800 border-green-200",
  moq_reached: "bg-blue-100 text-blue-800 border-blue-200",
  closed: "bg-gray-100 text-gray-600 border-gray-200",
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border",
        statusStyles[status],
        className
      )}
    >
      {status === "active" && (
        <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-green-500 inline-block" />
      )}
      {getStatusLabel(status)}
    </span>
  );
}
