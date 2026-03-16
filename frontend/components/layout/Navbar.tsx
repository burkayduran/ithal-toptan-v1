"use client";

import Link from "next/link";
import { useAuthStore } from "@/features/auth/store";
import { Button } from "@/components/ui/button";
import { ShoppingBag, User, LogOut } from "lucide-react";
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

export default function Navbar() {
  const { user, isHydrated, hydrate, logout, openAuthModal } = useAuthStore();
  const queryClient = useQueryClient();

  // Hydrate auth state once on mount (async – fetches /auth/me if token exists)
  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const handleLogout = () => {
    logout();
    // Clear protected cached data so stale wishlist data is not shown
    queryClient.removeQueries({ queryKey: ["wishlist"] });
  };

  // Derive display name: prefer full_name, fall back to email prefix
  const displayName = user
    ? (user.full_name?.split(" ")[0] ?? user.email.split("@")[0])
    : null;

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex h-16 items-center justify-between">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 font-bold text-xl tracking-tight text-gray-900"
        >
          <ShoppingBag className="h-6 w-6 text-blue-600" />
          <span>
            İthal <span className="text-blue-600">Toptan</span>
          </span>
        </Link>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-gray-600">
          <Link href="/" className="hover:text-gray-900 transition-colors">
            Kampanyalar
          </Link>
          <Link href="/my-campaigns" className="hover:text-gray-900 transition-colors">
            Siparişlerim
          </Link>
        </nav>

        {/* Auth actions – hidden until hydration completes to prevent flash */}
        <div className="flex items-center gap-3">
          {!isHydrated ? (
            <div className="h-8 w-24 rounded-md bg-gray-100 animate-pulse" />
          ) : user ? (
            <>
              <Link href="/my-campaigns">
                <Button variant="ghost" size="sm" className="gap-2 hidden sm:flex">
                  <User className="h-4 w-4" />
                  {displayName}
                </Button>
              </Link>
              <Button variant="ghost" size="sm" onClick={handleLogout} className="gap-2">
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Çıkış</span>
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={() => openAuthModal()}>
                Giriş Yap
              </Button>
              <Button size="sm" onClick={() => openAuthModal()}>
                Kayıt Ol
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
