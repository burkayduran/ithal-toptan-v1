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

export function useRegister() {
  const { setAuth, consumePostAuthAction, closeAuthModal } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: RegisterPayload) => {
      const tokenData = await register(payload);
      storeToken(tokenData.access_token);
      const user = await getMe();
      return { token: tokenData.access_token, user };
    },
    onSuccess: ({ token, user }) => {
      setAuth(token, user);
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
      consumePostAuthAction();
      closeAuthModal();
    },
  });
}
