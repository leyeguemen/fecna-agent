"use client";

import { useState } from "react";

import {
  faRightFromBracket,
  faRightToBracket,
  faUser,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { AuthDialog } from "@/components/auth/auth-dialog";
import { Button } from "@/components/ui/button";
import { useUser } from "@/lib/auth";

function truncateEmail(email: string, max = 20): string {
  return email.length > max ? `${email.slice(0, max - 1)}…` : email;
}

/** Botón de sesión: "Ingresar" abre el diálogo de auth; con sesión activa
 * muestra el email (truncado), una insignia "admin" si aplica, y "Cerrar
 * sesión". */
export function SessionButton() {
  const { user, loading, logout } = useUser();
  const [dialogOpen, setDialogOpen] = useState(false);

  if (loading) {
    return (
      <Button size="sm" disabled>
        <FontAwesomeIcon icon={faRightToBracket} className="size-3.5" />
        Ingresar
      </Button>
    );
  }

  if (!user) {
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
    <div className="flex items-center gap-2">
      {user.role === "admin" && (
        <span className="rounded-full bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground">
          admin
        </span>
      )}
      <span
        className="inline-flex max-w-[12rem] items-center gap-1.5 truncate text-sm text-muted-foreground"
        title={user.email}
      >
        <FontAwesomeIcon icon={faUser} className="size-3.5 shrink-0" />
        {truncateEmail(user.email)}
      </span>
      <Button variant="outline" size="sm" onClick={logout}>
        <FontAwesomeIcon icon={faRightFromBracket} className="size-3.5" />
        Cerrar sesión
      </Button>
    </div>
  );
}
