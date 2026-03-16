"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface TimeLeft {
  days: number;
  hours: number;
  minutes: number;
  expired: boolean;
}

function getTimeLeft(deadline: string): TimeLeft {
  const diff = new Date(deadline).getTime() - Date.now();
  if (diff <= 0) return { days: 0, hours: 0, minutes: 0, expired: true };
  return {
    days: Math.floor(diff / (1000 * 60 * 60 * 24)),
    hours: Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
    minutes: Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60)),
    expired: false,
  };
}

interface CountdownBlockProps {
  deadline: string;
  /** compact=true renders as a single inline span for use inside cards */
  compact?: boolean;
  className?: string;
}

export default function CountdownBlock({
  deadline,
  compact = false,
  className,
}: CountdownBlockProps) {
  const [timeLeft, setTimeLeft] = useState<TimeLeft>(getTimeLeft(deadline));

  useEffect(() => {
    const id = setInterval(() => setTimeLeft(getTimeLeft(deadline)), 60_000);
    return () => clearInterval(id);
  }, [deadline]);

  if (timeLeft.expired) {
    return (
      <span
        className={cn(
          compact ? "text-xs font-semibold" : "text-base font-bold",
          "text-red-600",
          className
        )}
      >
        Süre doldu
      </span>
    );
  }

  if (compact) {
    const parts = [];
    if (timeLeft.days > 0) parts.push(`${timeLeft.days}g`);
    parts.push(`${String(timeLeft.hours).padStart(2, "0")}s`);
    parts.push(`${String(timeLeft.minutes).padStart(2, "0")}d`);
    return (
      <span
        className={cn(
          "text-xs font-semibold tabular-nums",
          timeLeft.days === 0 && timeLeft.hours < 6
            ? "text-red-600"
            : "text-orange-700",
          className
        )}
      >
        {parts.join(" ")}
      </span>
    );
  }

  const isUrgent = timeLeft.days === 0 && timeLeft.hours < 6;
  const colorClass = isUrgent ? "text-red-700 bg-red-50 border-red-200" : "text-orange-700 bg-orange-50 border-orange-200";

  return (
    <div className={cn("flex items-center gap-3", className)}>
      {[
        { value: timeLeft.days, label: "Gün" },
        { value: timeLeft.hours, label: "Saat" },
        { value: timeLeft.minutes, label: "Dakika" },
      ].map(({ value, label }) => (
        <div
          key={label}
          className={cn(
            "flex flex-col items-center border rounded-xl px-4 py-3 min-w-[72px]",
            colorClass
          )}
        >
          <span className="text-3xl font-bold tabular-nums leading-none">
            {String(value).padStart(2, "0")}
          </span>
          <span className="text-xs mt-1 opacity-70">{label}</span>
        </div>
      ))}
    </div>
  );
}
