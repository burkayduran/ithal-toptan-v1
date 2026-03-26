import { cn } from "@/lib/utils";
import { type LucideIcon } from "lucide-react";

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  className?: string;
  icon?: LucideIcon;
  iconColor?: string; // e.g. "bg-orange-500", "bg-green-500"
  action?: React.ReactNode;
}

export default function SectionHeader({
  title,
  subtitle,
  className,
  icon: Icon,
  iconColor = "bg-indigo-500",
  action,
}: SectionHeaderProps) {
  return (
    <div className={cn("flex items-center justify-between mb-8", className)}>
      <div className="flex items-center gap-3">
        {Icon && (
          <div className={`p-2 ${iconColor} rounded-lg shadow-sm`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
        )}
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-gray-900">
            {title}
          </h2>
          {subtitle && (
            <p className="mt-0.5 text-sm text-gray-500">{subtitle}</p>
          )}
        </div>
      </div>
      {action && action}
    </div>
  );
}
