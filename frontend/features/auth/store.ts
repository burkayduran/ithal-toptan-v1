"use client";

import { create } from "zustand";
import { User } from "./types";
import { getMockCurrentUser, mockLogout } from "./mock";

interface AuthStore {
  user: User | null;
  isAuthModalOpen: boolean;
  postAuthAction: (() => void) | null;
  setUser: (user: User | null) => void;
  openAuthModal: (postAuthAction?: () => void) => void;
  closeAuthModal: () => void;
  logout: () => void;
  hydrate: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  isAuthModalOpen: false,
  postAuthAction: null,

  setUser: (user) => set({ user }),

  openAuthModal: (postAuthAction) =>
    set({ isAuthModalOpen: true, postAuthAction: postAuthAction ?? null }),

  closeAuthModal: () =>
    set({ isAuthModalOpen: false, postAuthAction: null }),

  logout: () => {
    mockLogout();
    set({ user: null });
  },

  // Call once on app mount to restore session from localStorage
  hydrate: () => {
    const user = getMockCurrentUser();
    set({ user });
  },
}));
