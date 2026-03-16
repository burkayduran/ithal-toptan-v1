import { useMutation, useQueryClient } from "@tanstack/react-query";
import { login, register, getMe } from "./api";
import { LoginPayload, RegisterPayload } from "./types";
import { useAuthStore } from "./store";
import { storeToken } from "@/lib/api/client";

export function useLogin() {
  const { setAuth, closeAuthModal, postAuthAction } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: LoginPayload) => {
      const tokenData = await login(payload);
      // Persist token so getMe() can attach the Authorization header
      storeToken(tokenData.access_token);
      const user = await getMe();
      return { token: tokenData.access_token, user };
    },
    onSuccess: ({ token, user }) => {
      setAuth(token, user);
      closeAuthModal();
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
      postAuthAction?.();
    },
  });
}

export function useRegister() {
  const { setAuth, closeAuthModal, postAuthAction } = useAuthStore();
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
      closeAuthModal();
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
      postAuthAction?.();
    },
  });
}
