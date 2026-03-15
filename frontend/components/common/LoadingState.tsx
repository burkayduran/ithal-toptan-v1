import { Loader2 } from "lucide-react";

interface LoadingStateProps {
  message?: string;
}

export default function LoadingState({ message = "Yükleniyor..." }: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-4" />
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  );
}
