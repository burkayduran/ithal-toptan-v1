import { cn } from "@/lib/utils";

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  className?: string;
}

export default function SectionHeader({ title, subtitle, className }: SectionHeaderProps) {
  return (
    <div className={cn("mb-8", className)}>
      <h2 className="text-2xl font-bold tracking-tight text-gray-900">{title}</h2>
      {subtitle && (
        <p className="mt-1.5 text-sm text-gray-500">{subtitle}</p>
      )}
    </div>
  );
}
