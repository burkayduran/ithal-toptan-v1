import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorState({
  message = "Bir hata oluştu. Lütfen tekrar deneyin.",
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center px-4">
      <div className="rounded-full bg-red-50 p-5 mb-5">
        <AlertCircle className="h-10 w-10 text-red-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900">Hata</h3>
      <p className="mt-2 text-sm text-gray-500 max-w-sm">{message}</p>
      {onRetry && (
        <Button variant="outline" className="mt-6" onClick={onRetry}>
          Tekrar Dene
        </Button>
      )}
    </div>
  );
}
