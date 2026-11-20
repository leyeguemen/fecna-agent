"use client";

import { useEffect, useState } from "react";
import { Copy, Printer } from "lucide-react";

import { Button } from "@/components/ui/button";

/** Botones "Copiar enlace" e "Imprimir / PDF". Ocultos al imprimir (esta
 * barra no debe aparecer en el documento resultante). */
export function FichaActions() {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 2000);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
    } catch {
      // Portapapeles no disponible (permiso denegado, navegador antiguo,
      // etc.); no hay una acción de respaldo razonable, así que solo
      // evitamos que la excepción quede sin manejar.
    }
  }

  return (
    <div className="flex items-center justify-end gap-2 print:hidden">
      <Button variant="outline" size="sm" onClick={handleCopy}>
        <Copy data-icon="inline-start" />
        {copied ? "¡Enlace copiado!" : "Copiar enlace"}
      </Button>
      <Button variant="outline" size="sm" onClick={() => window.print()}>
        <Printer data-icon="inline-start" />
        Imprimir / PDF
      </Button>
    </div>
  );
}
