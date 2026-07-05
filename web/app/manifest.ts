import type { MetadataRoute } from "next";

/**
 * Manifest PWA (Next.js sirve esto en /manifest.webmanifest automáticamente).
 * Íconos placeholder generados a partir de un SVG con el emoji 🏊 sobre
 * fondo sólido — ver web/README.md para cómo reemplazarlos por artwork real.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "FECNA Natación",
    short_name: "FECNA",
    description:
      "Rankings, fichas de nadadores y programas de campeonato de FECNA.",
    start_url: "/",
    display: "standalone",
    lang: "es",
    background_color: "#ffffff",
    theme_color: "#0369a1",
    icons: [
      {
        src: "/icons/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-512-maskable.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
