"use client";

import { create } from "zustand";
import { User } from "./types";
import { storeToken } from "@/lib/api/client";

const TOKEN_KEY = "auth_token";

function loadToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

interface AuthStore {
  token: string | null;
  user: User | null;
  /** True once the initial localStorage → /auth/me check has completed. */
  isHydrated: boolean;
  isAuthModalOpen: boolean;
  postAuthAction: (() => void) | null;

  /** Called after successful login or register. */
  setAuth: (token: string, user: User) => void;
  setUser: (user: User | null) => void;
  openAuthModal: (postAuthAction?: () => void) => void;
  closeAuthModal: () => void;
  logout: () => void;
  /** Run once on app mount – restores session from localStorage. */
  hydrate: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  token: null,
  user: null,
  isHydrated: false,
  isAuthModalOpen: false,
  postAuthAction: null,

  setAuth: (token, user) => {
    storeToken(token);
    set({ token, user });
  },

  setUser: (user) => set({ user }),

  openAuthModal: (postAuthAction) =>
    set({ isAuthModalOpen: true, postAuthAction: postAuthAction ?? null }),

  closeAuthModal: () => set({ isAuthModalOpen: false, postAuthAction: null }),

  logout: () => {
    storeToken(null);
    set({ token: null, user: null });
  },

  hydrate: async () => {
    // Guard: only hydrate once
    if (get().isHydrated) return;

    const token = loadToken();
    if (!token) {
      set({ isHydrated: true });
      return;
    }

    try {
      // Token is already in localStorage so the API client will attach it
      const { getMe } = await import("./api");
      const user = await getMe();
      set({ token, user, isHydrated: true });
    } catch {
      // Token is expired or invalid – clear it
      storeToken(null);
      set({ token: null, user: null, isHydrated: true });
    }
  },
}));
