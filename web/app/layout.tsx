import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Script from "next/script";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

import "./globals.css";

// Nombres de variable alineados con `--font-sans` / `--font-mono` en
// globals.css (@theme inline) para que Tailwind resuelva la fuente real en
// vez de quedarse con la referencia circular que deja el preset por defecto.
const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "FECNA Natación",
    template: "%s · FECNA Natación",
  },
  description:
    "Rankings, fichas de nadadores y programas de campeonato de FECNA.",
  applicationName: "FECNA Natación",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "FECNA Natación",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
};

// Evita el parpadeo de tema: aplica la clase "dark" antes de hidratar, según
// la preferencia guardada (localStorage) o, si no hay ninguna, la del
// sistema. Ver components/theme-toggle.tsx para el toggle persistido.
const THEME_INIT_SCRIPT = `
(function () {
  try {
    var stored = window.localStorage.getItem("fecna-theme");
    var dark = stored ? stored === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (dark) document.documentElement.classList.add("dark");
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} flex min-h-screen flex-col antialiased`}
      >
        <Script
          id="theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }}
        />
        <SiteHeader />
        <main className="flex-1">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
