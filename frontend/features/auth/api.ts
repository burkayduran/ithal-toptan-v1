import { User, LoginPayload, RegisterPayload } from "./types";
import { mockLogin, mockRegister, getMockCurrentUser, mockLogout } from "./mock";

const delay = (ms = 500) => new Promise((r) => setTimeout(r, ms));

export async function login(payload: LoginPayload): Promise<User> {
  await delay();
  return mockLogin(payload.email, payload.password);
}

export async function register(payload: RegisterPayload): Promise<User> {
  await delay();
  return mockRegister(payload.email, payload.password, payload.fullName);
}

export async function getCurrentUser(): Promise<User | null> {
  return getMockCurrentUser();
}

export async function logout(): Promise<void> {
  mockLogout();
}
