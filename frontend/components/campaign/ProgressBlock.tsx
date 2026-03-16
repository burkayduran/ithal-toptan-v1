import { Progress } from "@/components/ui/progress";
import { calculateProgress, calculateRemaining } from "@/lib/utils/calculateRemaining";
import { Package } from "lucide-react";

interface ProgressBlockProps {
  currentCount: number;
  targetCount: number;
  compact?: boolean;
}

export default function ProgressBlock({ currentCount, targetCount, compact }: ProgressBlockProps) {
  const progress = calculateProgress(currentCount, targetCount);
  const remaining = calculateRemaining(currentCount, targetCount);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-1.5 font-medium text-gray-700">
          <Package className="h-3.5 w-3.5 text-gray-400" />
          {currentCount} / {targetCount} adet
        </span>
        {remaining > 0 ? (
          <span className="text-gray-500 text-xs">{remaining} adet kaldı</span>
        ) : (
          <span className="text-green-600 text-xs font-semibold">Hedef doldu!</span>
        )}
      </div>
      <Progress value={progress} className="h-2" />
      {!compact && (
        <p className="text-xs text-gray-400 text-right">{progress}% tamamlandı</p>
      )}
    </div>
  );
}
