"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/features/auth/store";
import { Button } from "@/components/ui/button";
import { Heart, LogOut, Menu, X } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

export default function Navbar() {
  const pathname = usePathname();
  if (pathname.startsWith("/admin")) return null;
  const { user, isHydrated, logout, openAuthModal } = useAuthStore();
  const queryClient = useQueryClient();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    logout();
    queryClient.removeQueries({ queryKey: ["wishlist"] });
    queryClient.removeQueries({ queryKey: ["payment"] });
    queryClient.removeQueries({ queryKey: ["status"] });
    queryClient.removeQueries({ queryKey: ["admin"] });
  };

  const displayName = user
    ? (user.full_name?.split(" ")[0] ?? user.email.split("@")[0])
    : null;

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex h-16 items-center justify-between">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2.5 font-bold text-xl tracking-tight text-gray-900"
        >
          <div className="w-9 h-9 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-sm">
            <Heart className="h-5 w-5 text-white" />
          </div>
          <span>
            İthal <span className="text-indigo-600">Toptan</span>
          </span>
        </Link>

        {/* Desktop nav — no admin link; admin panel is at /admin directly */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-gray-600">
          <Link
            href="/campaigns"
            className="hover:text-indigo-600 transition-colors"
          >
            Kampanyalar
          </Link>
          <Link
            href="/my-campaigns"
            className="hover:text-indigo-600 transition-colors"
          >
            Siparişlerim
          </Link>
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-3">
          {!isHydrated ? (
            <div className="h-8 w-24 rounded-md bg-gray-100 animate-pulse" />
          ) : user ? (
            <>
              <Link href="/my-campaigns">
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-2 hidden sm:flex"
                >
                  <div className="w-7 h-7 bg-gradient-to-br from-indigo-400 to-purple-500 rounded-full flex items-center justify-center">
                    <span className="text-white text-xs font-medium">
                      {displayName?.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  {displayName}
                </Button>
              </Link>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="gap-2"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Çıkış</span>
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => openAuthModal(undefined, "login")}
                className="text-gray-700 hover:text-indigo-600"
              >
                Giriş Yap
              </Button>
              <Button
                size="sm"
                onClick={() => openAuthModal(undefined, "register")}
                className="bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                Kayıt Ol
              </Button>
            </>
          )}

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden p-2 text-gray-600"
          >
            {mobileOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile menu — no admin link */}
      {mobileOpen && (
        <div className="md:hidden bg-white border-t">
          <div className="px-4 py-4 space-y-3">
            <Link
              href="/campaigns"
              className="block text-gray-700 hover:text-indigo-600 font-medium"
              onClick={() => setMobileOpen(false)}
            >
              Kampanyalar
            </Link>
            <Link
              href="/my-campaigns"
              className="block text-gray-700 hover:text-indigo-600 font-medium"
              onClick={() => setMobileOpen(false)}
            >
              Siparişlerim
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
