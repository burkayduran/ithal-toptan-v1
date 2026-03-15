import { PackageOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

interface EmptyStateProps {
  title: string;
  description?: string;
  actionLabel?: string;
  actionHref?: string;
}

export default function EmptyState({
  title,
  description,
  actionLabel,
  actionHref,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center px-4">
      <div className="rounded-full bg-gray-100 p-5 mb-5">
        <PackageOpen className="h-10 w-10 text-gray-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      {description && (
        <p className="mt-2 text-sm text-gray-500 max-w-sm">{description}</p>
      )}
      {actionLabel && actionHref && (
        <Link href={actionHref}>
          <Button className="mt-6">{actionLabel}</Button>
        </Link>
      )}
    </div>
  );
}
