"use client";

import { useEffect, useState } from "react";
import { useRegister } from "@/features/auth/hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, CheckCircle2 } from "lucide-react";

interface RegisterFormProps {
  onSwitchToLogin: () => void;
}

export default function RegisterForm({ onSwitchToLogin }: RegisterFormProps) {
  const [full_name, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { mutate: register, isPending, error, isSuccess } = useRegister();

  // After successful registration, switch to login tab automatically
  useEffect(() => {
    if (!isSuccess) return;
    const timer = setTimeout(onSwitchToLogin, 2000);
    return () => clearTimeout(timer);
  }, [isSuccess, onSwitchToLogin]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    register({ email, password, full_name });
  };

  // Success state — show confirmation, auto-redirect to login
  if (isSuccess) {
    return (
      <div className="space-y-4 text-center py-2">
        <div className="flex justify-center">
          <CheckCircle2 className="h-10 w-10 text-green-500" />
        </div>
        <div>
          <p className="font-semibold text-gray-900">Hesabınız oluşturuldu!</p>
          <p className="text-sm text-gray-500 mt-1">
            Şimdi giriş yapabilirsiniz.
          </p>
        </div>
        <Button variant="outline" className="w-full" onClick={onSwitchToLogin}>
          Giriş Yap
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="reg-name">Ad Soyad</Label>
        <Input
          id="reg-name"
          type="text"
          placeholder="Ahmet Yılmaz"
          value={full_name}
          onChange={(e) => setFullName(e.target.value)}
          required
          autoComplete="name"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="reg-email">E-posta</Label>
        <Input
          id="reg-email"
          type="email"
          placeholder="ornek@email.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="reg-password">Şifre</Label>
        <Input
          id="reg-password"
          type="password"
          placeholder="En az 6 karakter"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={6}
          autoComplete="new-password"
        />
      </div>

      {error && (
        <p className="text-sm text-red-600 rounded-md bg-red-50 px-3 py-2">
          {(error as Error).message}
        </p>
      )}

      <Button type="submit" className="w-full" disabled={isPending}>
        {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Hesap Oluştur
      </Button>

      <p className="text-center text-sm text-gray-500">
        Zaten hesabınız var mı?{" "}
        <button
          type="button"
          className="text-blue-600 font-medium hover:underline"
          onClick={onSwitchToLogin}
        >
          Giriş Yap
        </button>
      </p>
    </form>
  );
}
