import { Users, TrendingUp, CheckCircle } from "lucide-react";

interface ProgressBlockProps {
  currentCount: number;
  targetCount: number;
  compact?: boolean;
}

export default function ProgressBlock({
  currentCount,
  targetCount,
  compact,
}: ProgressBlockProps) {
  const percentage =
    targetCount > 0
      ? Math.min(100, Math.round((currentCount / targetCount) * 100))
      : 0;
  const remaining = Math.max(0, targetCount - currentCount);
  const isReached = remaining === 0;

  /* Tailwind class-based gradients — no inline style except width */
  const barColor = isReached
    ? "bg-gradient-to-r from-green-400 to-emerald-500"
    : percentage > 80
    ? "bg-gradient-to-r from-yellow-400 to-orange-500"
    : "bg-gradient-to-r from-indigo-500 to-purple-500";

  const barHeight = compact ? "h-1.5" : "h-2.5";

  return (
    <div className="space-y-2">
      {/* Progress bar */}
      <div
        className={`w-full bg-gray-200 rounded-full overflow-hidden ${barHeight}`}
      >
        <div
          className={`h-full rounded-full transition-all duration-500 ease-out ${barColor}`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Meta row */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-1">
          <Users className="w-3.5 h-3.5 text-gray-500" />
          <span className="text-gray-600">
            <span className="font-semibold text-gray-900">{currentCount}</span>
            <span className="text-gray-400"> / {targetCount}</span>
          </span>
        </div>

        {isReached ? (
          <div className="flex items-center gap-1 text-green-600">
            <CheckCircle className="w-3.5 h-3.5" />
            <span className="text-xs font-medium">Talep tamamlandı</span>
          </div>
        ) : (
          <div className="flex items-center gap-1 text-gray-500">
            <TrendingUp className="w-3.5 h-3.5" />
            <span className="text-xs">
              <span className="font-medium text-indigo-600">{remaining}</span>{" "}
              adet kaldı
            </span>
          </div>
        )}
      </div>

      {/* Extended percentage — only in non-compact mode */}
      {!compact && (
        <p className="text-xs text-gray-400 text-right">
          %{percentage} tamamlandı
        </p>
      )}
    </div>
  );
}
