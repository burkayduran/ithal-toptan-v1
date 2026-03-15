import { useMutation } from "@tanstack/react-query";
import { login, register } from "./api";
import { LoginPayload, RegisterPayload } from "./types";
import { useAuthStore } from "./store";

export function useLogin() {
  const { setUser, closeAuthModal, postAuthAction } = useAuthStore();

  return useMutation({
    mutationFn: (payload: LoginPayload) => login(payload),
    onSuccess: (user) => {
      setUser(user);
      closeAuthModal();
      // Fire the deferred action (e.g., join wishlist) after login
      postAuthAction?.();
    },
  });
}

export function useRegister() {
  const { setUser, closeAuthModal, postAuthAction } = useAuthStore();

  return useMutation({
    mutationFn: (payload: RegisterPayload) => register(payload),
    onSuccess: (user) => {
      setUser(user);
      closeAuthModal();
      postAuthAction?.();
    },
  });
}
