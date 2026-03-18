"use client";

import { useEffect } from "react";
import { useAuthStore } from "@/features/auth/store";

/**
 * Triggers auth hydration once on app mount (reads token from localStorage → /me).
 * Placed in root layout so all routes — including admin — benefit immediately.
 * Navbar no longer needs to own this side-effect.
 */
export default function AuthBootstrap() {
  const hydrate = useAuthStore((s) => s.hydrate);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  return null;
}
