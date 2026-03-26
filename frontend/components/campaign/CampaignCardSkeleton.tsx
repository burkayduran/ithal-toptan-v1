export default function CampaignCardSkeleton() {
  return (
    <div className="bg-white rounded-2xl overflow-hidden border border-gray-100 animate-pulse flex flex-col shadow-sm">
      {/* Image placeholder */}
      <div className="aspect-square bg-gray-200" />

      {/* Content */}
      <div className="p-4 space-y-3 flex-1 flex flex-col">
        {/* Status pill */}
        <div className="h-5 bg-indigo-100 rounded-full w-28" />
        {/* Title */}
        <div className="h-4 bg-gray-200 rounded w-3/4" />
        {/* Price */}
        <div className="h-6 bg-gray-200 rounded w-24" />
        {/* Progress bar */}
        <div className="mt-auto space-y-2">
          <div className="h-1.5 bg-gray-200 rounded-full" />
          <div className="flex justify-between">
            <div className="h-3 bg-gray-200 rounded w-16" />
            <div className="h-3 bg-gray-200 rounded w-20" />
          </div>
        </div>
        {/* CTA */}
        <div className="h-10 bg-gray-100 rounded-xl" />
      </div>
    </div>
  );
}
