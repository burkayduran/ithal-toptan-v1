"use client";

import { useAuthStore } from "@/features/auth/store";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import LoginForm from "./LoginForm";
import RegisterForm from "./RegisterForm";

export default function AuthModal() {
  const { isAuthModalOpen, closeAuthModal, authModalTab, setAuthModalTab } = useAuthStore();

  return (
    <Dialog open={isAuthModalOpen} onOpenChange={(open) => !open && closeAuthModal()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-center text-xl">
            {authModalTab === "login" ? "Giriş Yap" : "Kayıt Ol"}
          </DialogTitle>
        </DialogHeader>

        <Tabs
          value={authModalTab}
          onValueChange={(v) => setAuthModalTab(v as "login" | "register")}
        >
          <TabsList className="grid w-full grid-cols-2 mb-4">
            <TabsTrigger value="login">Giriş</TabsTrigger>
            <TabsTrigger value="register">Kayıt</TabsTrigger>
          </TabsList>

          <TabsContent value="login">
            <LoginForm onSwitchToRegister={() => setAuthModalTab("register")} />
          </TabsContent>

          <TabsContent value="register">
            <RegisterForm onSwitchToLogin={() => setAuthModalTab("login")} />
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
