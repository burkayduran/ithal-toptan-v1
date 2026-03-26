import type { Metadata } from "next";
import "./globals.css";
import QueryProvider from "@/components/providers/QueryProvider";
import AuthBootstrap from "@/components/providers/AuthBootstrap";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import AuthModal from "@/components/auth/AuthModal";
import { Toaster } from "@/components/ui/sonner";

export const metadata: Metadata = {
  title: "İthal Toptan – Grup Alımıyla Toptan Fiyat",
  description:
    "MOQ bazlı grup alım platformu. Premium ürünleri toptan fiyatına alın.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="tr">
      <body className="font-sans antialiased bg-gray-50 text-gray-900 flex flex-col min-h-screen">
        <QueryProvider>
          <AuthBootstrap />
          <Navbar />
          <div className="flex-1">{children}</div>
          <Footer />
          <AuthModal />
          <Toaster position="bottom-right" />
        </QueryProvider>
      </body>
    </html>
  );
}
