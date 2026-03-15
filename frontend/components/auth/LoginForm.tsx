"use client";

import { useState } from "react";
import { useLogin } from "@/features/auth/hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";

interface LoginFormProps {
  onSwitchToRegister: () => void;
}

export default function LoginForm({ onSwitchToRegister }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { mutate: login, isPending, error } = useLogin();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login({ email, password });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="login-email">E-posta</Label>
        <Input
          id="login-email"
          type="email"
          placeholder="ornek@email.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="login-password">Şifre</Label>
        <Input
          id="login-password"
          type="password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />
      </div>

      {error && (
        <p className="text-sm text-red-600">{(error as Error).message}</p>
      )}

      <Button type="submit" className="w-full" disabled={isPending}>
        {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Giriş Yap
      </Button>

      <p className="text-center text-sm text-gray-500">
        Hesabınız yok mu?{" "}
        <button
          type="button"
          className="text-blue-600 font-medium hover:underline"
          onClick={onSwitchToRegister}
        >
          Kayıt Ol
        </button>
      </p>

      {/* Demo hint */}
      <p className="text-center text-xs text-gray-400 border-t pt-3">
        Demo: demo@ithal.com / demo123
      </p>
    </form>
  );
}
