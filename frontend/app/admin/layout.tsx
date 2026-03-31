"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/store";
import AdminSidebar from "@/components/admin/AdminSidebar";
import { LogOut, ExternalLink } from "lucide-react";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, isHydrated, logout } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (isHydrated && (!user || !user.is_admin)) {
      router.replace("/");
    }
  }, [isHydrated, user, router]);

  if (!isHydrated) {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-gray-500 bg-gray-50">
        Yükleniyor...
      </div>
    );
  }

  if (!user || !user.is_admin) {
    return null;
  }

  const displayName = user.full_name?.split(" ")[0] ?? user.email.split("@")[0];

  function handleLogout() {
    logout();
    queryClient.clear();
    router.push("/");
  }

  return (
    <div className="flex flex-col min-h-screen">
      {/* Admin top bar */}
      <header className="h-11 bg-gray-950 border-b border-gray-800 flex items-center justify-between px-4 flex-shrink-0 z-50">
        <span className="text-xs font-bold uppercase tracking-widest text-gray-500">
          Admin Panel
        </span>
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="text-xs text-gray-400 hover:text-gray-200 transition-colors flex items-center gap-1"
          >
            <ExternalLink className="h-3 w-3" />
            Siteye dön
          </Link>
          <span className="text-xs text-gray-500 hidden sm:inline">{displayName}</span>
          <button
            onClick={handleLogout}
            className="text-xs text-gray-400 hover:text-red-400 transition-colors flex items-center gap-1"
          >
            <LogOut className="h-3 w-3" />
            Çıkış
          </button>
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        <AdminSidebar />
        <main className="flex-1 overflow-y-auto bg-gray-50">{children}</main>
      </div>
    </div>
  );
}
