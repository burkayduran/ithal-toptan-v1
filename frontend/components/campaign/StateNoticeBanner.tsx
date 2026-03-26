import { cn } from "@/lib/utils";
import { AlertCircle, CheckCircle2, Info, XCircle } from "lucide-react";

type NoticeType = "info" | "warning" | "success" | "error";

interface StateNoticeBannerProps {
  type: NoticeType;
  title?: string;
  message: string;
  className?: string;
}

const STYLES: Record<NoticeType, { bg: string; border: string; text: string; icon: React.ElementType }> = {
  info: {
    bg: "bg-blue-50",
    border: "border-blue-200",
    text: "text-blue-800",
    icon: Info,
  },
  warning: {
    bg: "bg-amber-50",
    border: "border-amber-200",
    text: "text-amber-800",
    icon: AlertCircle,
  },
  success: {
    bg: "bg-green-50",
    border: "border-green-200",
    text: "text-green-800",
    icon: CheckCircle2,
  },
  error: {
    bg: "bg-red-50",
    border: "border-red-200",
    text: "text-red-800",
    icon: XCircle,
  },
};

export default function StateNoticeBanner({
  type,
  title,
  message,
  className,
}: StateNoticeBannerProps) {
  const { bg, border, text, icon: Icon } = STYLES[type];
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border px-4 py-3",
        bg,
        border,
        className
      )}
    >
      <Icon className={cn("h-4 w-4 mt-0.5 shrink-0", text)} />
      <div>
        {title && <p className={cn("text-sm font-semibold", text)}>{title}</p>}
        <p className={cn("text-sm", title ? "mt-0.5 opacity-90" : "", text)}>{message}</p>
      </div>
    </div>
  );
}
