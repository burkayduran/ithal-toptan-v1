export default function CampaignCardSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden animate-pulse">
      {/* Image placeholder */}
      <div className="aspect-[4/3] bg-gray-200" />

      {/* Content */}
      <div className="p-4 space-y-3">
        {/* Title */}
        <div className="space-y-1.5">
          <div className="h-4 bg-gray-200 rounded w-full" />
          <div className="h-4 bg-gray-200 rounded w-3/4" />
        </div>

        {/* Price */}
        <div className="h-6 bg-gray-200 rounded w-24" />

        {/* Progress bar */}
        <div className="space-y-1.5">
          <div className="flex justify-between">
            <div className="h-3 bg-gray-200 rounded w-20" />
            <div className="h-3 bg-gray-200 rounded w-14" />
          </div>
          <div className="h-2 bg-gray-200 rounded w-full" />
        </div>

        {/* CTA button */}
        <div className="h-9 bg-gray-200 rounded w-full" />
      </div>
    </div>
  );
}
