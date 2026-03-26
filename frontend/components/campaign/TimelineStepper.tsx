import { cn } from "@/lib/utils";
import { Check } from "lucide-react";
import type { PaymentStage } from "@/features/payments/types";

interface Step {
  id: PaymentStage;
  label: string;
  description: string;
}

const STEPS: Step[] = [
  { id: "campaign_active", label: "Kampanya Aktif", description: "Bekleme listesi oluşturuldu" },
  { id: "moq_reached", label: "Hedef Doldu", description: "Yeterli katılım sağlandı" },
  { id: "payment_confirmed", label: "Ödeme Tamamlandı", description: "Ödemeniz onaylandı" },
  { id: "order_placed", label: "Sipariş Verildi", description: "Tedarikçiye sipariş gönderildi" },
  { id: "shipping", label: "Kargoya Verildi", description: "Ürün yolda" },
  { id: "delivered", label: "Teslim Edildi", description: "Ürün teslim edildi" },
];

const STAGE_ORDER: PaymentStage[] = [
  "campaign_active",
  "moq_reached",
  "payment_confirmed",
  "order_placed",
  "shipping",
  "delivered",
];

interface TimelineStepperProps {
  currentStage: PaymentStage;
  className?: string;
}

export default function TimelineStepper({ currentStage, className }: TimelineStepperProps) {
  const currentIndex = STAGE_ORDER.indexOf(currentStage);

  return (
    <ol className={cn("space-y-0", className)}>
      {STEPS.map((step, i) => {
        const isDone = i < currentIndex;
        const isActive = i === currentIndex;
        const isPending = i > currentIndex;

        return (
          <li key={step.id} className="flex gap-4">
            {/* Track line + dot */}
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold transition-colors",
                  isDone && "border-green-500 bg-green-500 text-white",
                  isActive && "border-blue-600 bg-blue-600 text-white",
                  isPending && "border-gray-200 bg-white text-gray-400"
                )}
              >
                {isDone ? <Check className="h-4 w-4" /> : <span>{i + 1}</span>}
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={cn(
                    "mt-0.5 w-0.5 flex-1 min-h-[28px]",
                    i < currentIndex ? "bg-green-400" : "bg-gray-200"
                  )}
                />
              )}
            </div>

            {/* Label + description */}
            <div className="pb-6 pt-1">
              <p
                className={cn(
                  "text-sm font-semibold leading-none",
                  isDone && "text-green-700",
                  isActive && "text-blue-700",
                  isPending && "text-gray-400"
                )}
              >
                {step.label}
              </p>
              <p
                className={cn(
                  "mt-1 text-xs",
                  isPending ? "text-gray-300" : "text-gray-500"
                )}
              >
                {step.description}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
