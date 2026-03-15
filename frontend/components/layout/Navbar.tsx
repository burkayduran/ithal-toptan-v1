"use client";

import Link from "next/link";
import { useAuthStore } from "@/features/auth/store";
import { Button } from "@/components/ui/button";
import { ShoppingBag, User, LogOut } from "lucide-react";
import { useEffect } from "react";

export default function Navbar() {
  const { user, hydrate, logout, openAuthModal } = useAuthStore();

  // Restore auth state from localStorage on mount
  useEffect(() => {
    hydrate();
  }, [hydrate]);

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex h-16 items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 font-bold text-xl tracking-tight text-gray-900">
          <ShoppingBag className="h-6 w-6 text-blue-600" />
          <span>İthal <span className="text-blue-600">Toptan</span></span>
        </Link>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-gray-600">
          <Link href="/" className="hover:text-gray-900 transition-colors">Kampanyalar</Link>
          <Link href="/my-campaigns" className="hover:text-gray-900 transition-colors">Siparişlerim</Link>
        </nav>

        {/* Auth actions */}
        <div className="flex items-center gap-3">
          {user ? (
            <>
              <Link href="/my-campaigns">
                <Button variant="ghost" size="sm" className="gap-2 hidden sm:flex">
                  <User className="h-4 w-4" />
                  {user.fullName.split(" ")[0]}
                </Button>
              </Link>
              <Button variant="ghost" size="sm" onClick={logout} className="gap-2">
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
