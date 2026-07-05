import path from "node:path";

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Fija la raíz del workspace a este directorio: hay un package-lock.json
  // fuera del repo (en $HOME) que Next detecta como raíz candidata y genera
  // una advertencia al buildear. Ver
  // https://nextjs.org/docs/app/api-reference/config/next-config-js/turbopack#root-directory
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
