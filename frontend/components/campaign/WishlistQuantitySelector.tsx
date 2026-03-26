"use client";

import { Button } from "@/components/ui/button";
import { Minus, Plus } from "lucide-react";

interface WishlistQuantitySelectorProps {
  quantity: number;
  onChange: (qty: number) => void;
  min?: number;
  max?: number;
}

export default function WishlistQuantitySelector({
  quantity,
  onChange,
  min = 1,
  max = 50,
}: WishlistQuantitySelectorProps) {
  const decrement = () => onChange(Math.max(min, quantity - 1));
  const increment = () => onChange(Math.min(max, quantity + 1));

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm font-medium text-gray-700">Adet:</span>
      <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden">
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 rounded-none border-r"
          onClick={decrement}
          disabled={quantity <= min}
        >
          <Minus className="h-3.5 w-3.5" />
        </Button>
        <span className="w-12 text-center text-sm font-semibold select-none">
          {quantity}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 rounded-none border-l"
          onClick={increment}
          disabled={quantity >= max}
        >
          <Plus className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
