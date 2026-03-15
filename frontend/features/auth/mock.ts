import { User } from "./types";

const STORAGE_KEY = "auth_user";

// Mock user database
const mockUsers: (User & { password: string })[] = [
  { id: "demo1", email: "demo@ithal.com", fullName: "Demo Kullanıcı", password: "demo123" },
];

export function getMockCurrentUser(): User | null {
  if (typeof window === "undefined") return null;
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return null;
  try {
    return JSON.parse(stored) as User;
  } catch {
    return null;
  }
}

export function mockLogin(email: string, password: string): User {
  const user = mockUsers.find((u) => u.email === email && u.password === password);
  if (!user) throw new Error("E-posta veya şifre hatalı.");
  const { password: _, ...safeUser } = user;
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(safeUser));
  }
  return safeUser;
}

export function mockRegister(email: string, password: string, fullName: string): User {
  if (mockUsers.some((u) => u.email === email)) {
    throw new Error("Bu e-posta adresi zaten kayıtlı.");
  }
  const newUser: User & { password: string } = {
    id: `user_${Date.now()}`,
    email,
    fullName,
    password,
  };
  mockUsers.push(newUser);
  const { password: _, ...safeUser } = newUser;
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(safeUser));
  }
  return safeUser;
}

export function mockLogout(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(STORAGE_KEY);
  }
}
