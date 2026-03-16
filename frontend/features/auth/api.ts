import { api } from "@/lib/api/client";
import { AuthToken, User, LoginPayload, RegisterPayload } from "./types";

export async function login(payload: LoginPayload): Promise<AuthToken> {
  return api.post<AuthToken>("/api/v1/auth/login", payload);
}

export async function register(payload: RegisterPayload): Promise<AuthToken> {
  return api.post<AuthToken>("/api/v1/auth/register", payload);
}

export async function getMe(): Promise<User> {
  return api.get<User>("/api/v1/auth/me");
}
