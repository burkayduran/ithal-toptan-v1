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
  authModalTab: "login" | "register";
  postAuthAction: (() => void) | null;

  /** Called after successful login or register. */
  setAuth: (token: string, user: User) => void;
  setUser: (user: User | null) => void;
  openAuthModal: (postAuthAction?: () => void, tab?: "login" | "register") => void;
  closeAuthModal: () => void;
  setAuthModalTab: (tab: "login" | "register") => void;
  /**
   * Atomically reads, clears, and invokes postAuthAction.
   * Must be called BEFORE closeAuthModal so the action isn't wiped first.
   */
  consumePostAuthAction: () => void;
  logout: () => void;
  /** Run once on app mount – restores session from localStorage. */
  hydrate: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  token: null,
  user: null,
  isHydrated: false,
  isAuthModalOpen: false,
  authModalTab: "login",
  postAuthAction: null,

  setAuth: (token, user) => {
    storeToken(token);
    set({ token, user });
  },

  setUser: (user) => set({ user }),

  openAuthModal: (postAuthAction, tab = "login") =>
    set({ isAuthModalOpen: true, postAuthAction: postAuthAction ?? null, authModalTab: tab }),

  closeAuthModal: () =>
    set({ isAuthModalOpen: false, postAuthAction: null, authModalTab: "login" }),

  setAuthModalTab: (tab) => set({ authModalTab: tab }),

  consumePostAuthAction: () => {
    // Read the CURRENT store value (not a stale closure) then clear and run it
    const action = get().postAuthAction;
    set({ postAuthAction: null });
    action?.();
  },

  logout: () => {
    storeToken(null);
    set({ token: null, user: null });
  },

  hydrate: async () => {
    if (get().isHydrated) return;

    const token = loadToken();
    if (!token) {
      set({ isHydrated: true });
      return;
    }

    try {
      const { getMe } = await import("./api");
      const user = await getMe();
      set({ token, user, isHydrated: true });
    } catch {
      storeToken(null);
      set({ token: null, user: null, isHydrated: true });
    }
  },
}));
