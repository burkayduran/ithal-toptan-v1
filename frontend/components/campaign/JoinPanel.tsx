"use client";

import { useState } from "react";
import { Product } from "@/features/campaigns/types";
import { useAuthStore } from "@/features/auth/store";
import { useJoinWishlist } from "@/features/wishlist/hooks";
import { Button } from "@/components/ui/button";
import ProgressBlock from "./ProgressBlock";
import WishlistQuantitySelector from "./WishlistQuantitySelector";
import WishlistSuccessNotice from "./WishlistSuccessNotice";
import { Loader2, ShoppingCart } from "lucide-react";

interface JoinPanelProps {
  product: Product;
}

export default function JoinPanel({ product }: JoinPanelProps) {
  const [quantity, setQuantity] = useState(1);
  const [joined, setJoined] = useState(false);
  const { user, openAuthModal } = useAuthStore();
  const { mutate: joinWishlist, isPending, error } = useJoinWishlist();

  const handleJoin = () => {
    if (!user) {
      // Defer join action until after successful auth
      openAuthModal(() => {
        joinWishlist(
          { request_id: product.id, quantity },
          { onSuccess: () => setJoined(true) }
        );
      });
      return;
    }

    joinWishlist(
      { request_id: product.id, quantity },
      { onSuccess: () => setJoined(true) }
    );
  };

  if (joined) {
    return <WishlistSuccessNotice quantity={quantity} campaignTitle={product.title} />;
  }

  const canShowProgress =
    product.moq != null && product.current_wishlist_count != null;

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-5">
      {canShowProgress && (
        <ProgressBlock
          currentCount={product.current_wishlist_count!}
          targetCount={product.moq!}
        />
      )}

      {product.status === "active" ? (
        <>
          <WishlistQuantitySelector quantity={quantity} onChange={setQuantity} />

          {error && (
            <p className="text-sm text-red-600">
              {(error as Error).message || "Bir hata oluştu."}
            </p>
          )}

          <Button
            className="w-full gap-2"
            size="lg"
            onClick={handleJoin}
            disabled={isPending}
          >
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ShoppingCart className="h-4 w-4" />
            )}
            {isPending ? "Kaydediliyor..." : "Bekleme Listesine Katıl"}
          </Button>

          <p className="text-xs text-gray-400 text-center">
            Ödeme yalnızca MOQ dolduğunda talep edilir.
          </p>
        </>
      ) : product.status === "moq_reached" ? (
        <div className="text-center py-3">
          <p className="font-semibold text-blue-700">Hedef doldu!</p>
          <p className="text-sm text-gray-500 mt-1">Ödeme bildirimi bekleniyor.</p>
        </div>
      ) : product.status === "ordered" ? (
        <div className="text-center py-3">
          <p className="font-semibold text-purple-700">Sipariş verildi</p>
          <p className="text-sm text-gray-500 mt-1">Ürün tedarik aşamasında.</p>
        </div>
      ) : product.status === "delivered" ? (
        <div className="text-center py-3">
          <p className="font-semibold text-gray-700">Teslim edildi</p>
        </div>
      ) : (
        <div className="text-center py-3">
          <p className="text-sm text-gray-500">Bu kampanya şu an aktif değil.</p>
        </div>
      )}
    </div>
  );
}
