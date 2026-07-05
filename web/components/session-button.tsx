"use client";

import { Button } from "@/components/ui/button";

/** Placeholder de sesión: la tarea B2 lo conecta a /auth/login|register y al
 * estado real de sesión. Por ahora solo comunica que viene a continuación. */
export function SessionButton() {
  return (
    <Button variant="outline" size="sm" disabled title="Inicio de sesión: próximamente">
      Ingresar
    </Button>
  );
}
