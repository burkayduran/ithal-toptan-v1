import { Users } from "lucide-react";

interface ProgressBlockProps {
  currentCount: number;
  targetCount: number;
  compact?: boolean;
}

function getProgressGradient(percentage: number): string {
  if (percentage >= 100) return "linear-gradient(90deg, #6EE7B7, #10B981, #059669)";
  if (percentage >= 70) return "linear-gradient(90deg, #FBBF24, #F59E0B, #EA580C)";
  return "linear-gradient(90deg, #C4B5FD, #8B5CF6, #7C3AED)";
}

function getRemainingColor(percentage: number): string {
  if (percentage >= 100) return "text-emerald-600";
  if (percentage >= 70) return "text-orange-600";
  return "text-purple-600";
}

export default function ProgressBlock({ currentCount, targetCount, compact }: ProgressBlockProps) {
  const percentage = targetCount > 0 ? Math.min(100, Math.round((currentCount / targetCount) * 100)) : 0;
  const remaining = Math.max(0, targetCount - currentCount);

  return (
    <div className="space-y-1.5">
      {/* Gradient progress bar */}
      <div className="w-full h-[5px] bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500 ease-out"
          style={{
            width: `${percentage}%`,
            background: getProgressGradient(percentage),
          }}
        />
      </div>

      {/* Meta row */}
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-1 text-xs text-gray-500">
          <Users className="h-3.5 w-3.5" />
          <span className="font-medium text-gray-700">{currentCount}</span>
          <span>/ {targetCount}</span>
        </span>

        {remaining > 0 ? (
          <span className={`text-xs font-medium ${getRemainingColor(percentage)}`}>
            {remaining} adet kaldı
          </span>
        ) : (
          <span className="text-xs font-medium text-emerald-600">
            Talep tamamlandı
          </span>
        )}
      </div>

      {!compact && (
        <p className="text-xs text-gray-400 text-right">%{percentage} tamamlandı</p>
      )}
    </div>
  );
}
