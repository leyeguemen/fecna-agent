"use client";

import { useState } from "react";

import {
  faRightFromBracket,
  faRightToBracket,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { AuthDialog } from "@/components/auth/auth-dialog";
import { Button } from "@/components/ui/button";
import { useUser } from "@/lib/auth";

function truncateEmail(email: string, max = 20): string {
  return email.length > max ? `${email.slice(0, max - 1)}…` : email;
}

/** Control de sesión unificado con el user-menu visual de AdminLTE. */
export function SessionButton() {
  const { user, loading, logout } = useUser();
  const [dialogOpen, setDialogOpen] = useState(false);

  // La restauración de un token guardado puede depender de una API lenta o
  // no disponible. El usuario debe poder abrir el diálogo de ingreso mientras
  // esa comprobación termina; `loading` solo describe la sesión, no la
  // disponibilidad de esta acción.
  if (loading || !user) {
    return (
      <>
        <Button size="sm" onClick={() => setDialogOpen(true)}>
          <FontAwesomeIcon icon={faRightToBracket} className="size-3.5" />
          Ingresar
        </Button>
        <AuthDialog open={dialogOpen} onOpenChange={setDialogOpen} />
      </>
    );
  }

  return (
    <Button variant="outline" size="sm" onClick={logout}>
      <FontAwesomeIcon icon={faRightFromBracket} className="size-3.5" />
      Cerrar sesión de {truncateEmail(user.email)}
    </Button>
  );
}
