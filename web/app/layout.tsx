import type { Metadata, Viewport } from "next";
import { Geist_Mono, Source_Sans_3 } from "next/font/google";

import { config } from "@fortawesome/fontawesome-svg-core";
import "@adminlte/react/css";
import "bootstrap-icons/font/bootstrap-icons.css";
import "@fortawesome/fontawesome-svg-core/styles.css";

import { BootstrapClient } from "@/components/bootstrap-client";
import { AppShell } from "@/components/layout/app-shell";

import "./globals.css";

// Font Awesome: el CSS ya se importa arriba; sin esto inyectaría estilos en
// runtime y los iconos parpadearían gigantes en el primer paint (SSR).
config.autoAddCss = false;

// Nombres de variable alineados con `--font-sans` / `--font-mono` en
// globals.css para que Tailwind y AdminLTE compartan la tipografía de la app.
const sourceSans = Source_Sans_3({
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
    { media: "(prefers-color-scheme: light)", color: "#f8f9fa" },
    { media: "(prefers-color-scheme: dark)", color: "#2b3035" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body
        className={`${sourceSans.variable} ${geistMono.variable} app-loaded antialiased`}
      >
        <BootstrapClient />
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
