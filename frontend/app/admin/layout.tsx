"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/features/auth/store";
import AdminSidebar from "@/components/admin/AdminSidebar";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, isHydrated } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (isHydrated && (!user || !user.is_admin)) {
      router.replace("/");
    }
  }, [isHydrated, user, router]);

  if (!isHydrated) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-gray-500">
        Yükleniyor...
      </div>
    );
  }

  if (!user || !user.is_admin) {
    return null; // redirect fires in useEffect above
  }

  return (
    <div className="flex" style={{ minHeight: "calc(100vh - 64px)" }}>
      <AdminSidebar />
      <main className="flex-1 overflow-y-auto bg-gray-50">{children}</main>
    </div>
  );
}
