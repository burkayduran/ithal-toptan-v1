"use client";

import { useEffect } from "react";
import { useAuthStore } from "@/features/auth/store";

/**
 * Triggers auth hydration once on app mount (reads token from localStorage → /me).
 * Also listens for token expiry events to open the auth modal.
 */
export default function AuthBootstrap() {
  const hydrate = useAuthStore((s) => s.hydrate);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    const handler = () => {
      useAuthStore.getState().openAuthModal(undefined, "login");
    };
    window.addEventListener("auth:expired", handler);
    return () => window.removeEventListener("auth:expired", handler);
  }, []);

  return null;
}
