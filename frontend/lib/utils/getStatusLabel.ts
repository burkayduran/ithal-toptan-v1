import { ProductStatus } from "@/features/campaigns/types";

export function getStatusLabel(status: ProductStatus): string {
  switch (status) {
    case "active":
      return "Aktif";
    case "moq_reached":
      return "Hedef Doldu";
    case "payment_collecting":
      return "Ödeme Toplanıyor";
    case "ordered":
      return "Sipariş Verildi";
    case "delivered":
      return "Teslim Edildi";
    case "cancelled":
      return "İptal Edildi";
    case "pending":
      return "Beklemede";
    case "sourcing":
      return "Tedarik Ediliyor";
    default:
      return status;
  }
}

export function getStatusVariant(
  status: ProductStatus
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "active":
      return "default";
    case "moq_reached":
    case "payment_collecting":
    case "ordered":
    case "delivered":
      return "secondary";
    case "cancelled":
      return "destructive";
    default:
      return "outline";
  }
}
