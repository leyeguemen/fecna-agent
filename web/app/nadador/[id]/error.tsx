"use client";

import { Button } from "@/components/ui/button";

/** Boundary de error para la ficha: cubre fallos de red/servidor al pedir
 * el perfil (los 404 los maneja `not-found.tsx`, no llegan aquí). */
export default function FichaError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 px-4 py-24 text-center">
      <span className="text-4xl" aria-hidden="true">
        ⚠️
      </span>
      <h1 className="text-xl font-semibold tracking-tight">No se pudo cargar la ficha</h1>
      <p className="text-muted-foreground">
        Ocurrió un problema al conectar con el servidor. Intenta de nuevo.
      </p>
      <Button variant="outline" onClick={reset}>
        Reintentar
      </Button>
    </div>
  );
}
