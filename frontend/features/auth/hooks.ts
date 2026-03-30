import { useMutation, useQueryClient } from "@tanstack/react-query";
import { login, register, getMe } from "./api";
import { LoginPayload, RegisterPayload } from "./types";
import { useAuthStore } from "./store";
import { storeToken } from "@/lib/api/client";

export function useLogin() {
  const { setAuth, consumePostAuthAction, closeAuthModal } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: LoginPayload) => {
      const tokenData = await login(payload);
      storeToken(tokenData.access_token);
      const user = await getMe();
      return { token: tokenData.access_token, user };
    },
    onSuccess: ({ token, user }) => {
      setAuth(token, user);
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
      // consumePostAuthAction uses get() internally – always reads the live
      // store value, never a stale closure. Must run before closeAuthModal
      // which would also clear postAuthAction.
      consumePostAuthAction();
      closeAuthModal();
    },
  });
}

/**
 * Register — intentionally does NOT auto-login.
 * On success the caller should show a success message and redirect the user
 * to the login tab. Token from the backend is purposefully discarded.
 */
export function useRegister() {
  return useMutation({
    mutationFn: (payload: RegisterPayload) => register(payload),
    // No onSuccess side-effects: token is discarded, user stays logged out.
  });
}
