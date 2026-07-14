import type { Metadata, Viewport } from "next";
import { Geist_Mono, Source_Sans_3 } from "next/font/google";
import Script from "next/script";

import { config } from "@fortawesome/fontawesome-svg-core";
import "@fortawesome/fontawesome-svg-core/styles.css";

import { AppShell } from "@/components/layout/app-shell";

import "./globals.css";

// Font Awesome: el CSS ya se importa arriba; sin esto inyectaría estilos en
// runtime y los iconos parpadearían gigantes en el primer paint (SSR).
config.autoAddCss = false;

// Source Sans (la fuente de AdminLTE 3). Nombres de variable alineados con
// `--font-sans` / `--font-mono` en globals.css (@theme inline) para que
// Tailwind resuelva la fuente real en vez de quedarse con la referencia
// circular que deja el preset por defecto.
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
    { media: "(prefers-color-scheme: light)", color: "#f4f6f9" },
    { media: "(prefers-color-scheme: dark)", color: "#454d55" },
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
        className={`${sourceSans.variable} ${geistMono.variable} antialiased`}
      >
        <Script
          id="theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }}
        />
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
