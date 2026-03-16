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

  // Backend accepts wishlist join for ["active", "moq_reached"] only
  const canJoin = product.status === "active" || product.status === "moq_reached";

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-5">
      {canShowProgress && (
        <ProgressBlock
          currentCount={product.current_wishlist_count!}
          targetCount={product.moq!}
        />
      )}

      {canJoin ? (
        <>
          {product.status === "moq_reached" && (
            <div className="rounded-lg bg-blue-50 border border-blue-200 px-4 py-3 text-sm text-blue-800">
              <strong>Hedef doldu!</strong> Katılırsanız ödeme bildirimi alırsınız.
            </div>
          )}

          <WishlistQuantitySelector quantity={quantity} onChange={setQuantity} />

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">
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
            {isPending
              ? "Kaydediliyor..."
              : product.status === "moq_reached"
              ? "Ödeme Listesine Katıl"
              : "Bekleme Listesine Katıl"}
          </Button>

          <p className="text-xs text-gray-400 text-center">
            {product.status === "moq_reached"
              ? "Ödeme bildirimi almak için katılın."
              : "Ödeme yalnızca MOQ dolduğunda talep edilir."}
          </p>
        </>
      ) : product.status === "payment_collecting" ? (
        <div className="text-center py-4 space-y-1">
          <p className="font-semibold text-amber-700">Ödeme toplanıyor</p>
          <p className="text-sm text-gray-500">
            Bu kampanya için ödeme süreci başlamıştır. Yeni katılım alınmıyor.
          </p>
        </div>
      ) : product.status === "ordered" ? (
        <div className="text-center py-4 space-y-1">
          <p className="font-semibold text-purple-700">Sipariş verildi</p>
          <p className="text-sm text-gray-500">Ürün tedarik aşamasında.</p>
        </div>
      ) : product.status === "delivered" ? (
        <div className="text-center py-4">
          <p className="font-semibold text-gray-700">Teslim edildi</p>
        </div>
      ) : product.status === "cancelled" ? (
        <div className="text-center py-4">
          <p className="font-semibold text-red-600">Kampanya iptal edildi</p>
        </div>
      ) : (
        <div className="text-center py-4">
          <p className="text-sm text-gray-500">Bu kampanya şu an aktif değil.</p>
        </div>
      )}
    </div>
  );
}
