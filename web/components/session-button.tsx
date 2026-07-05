"use client";

import { useState } from "react";

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
      <Button variant="outline" size="sm" disabled>
        Ingresar
      </Button>
    );
  }

  if (!user) {
    return (
      <>
        <Button variant="outline" size="sm" onClick={() => setDialogOpen(true)}>
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
        className="max-w-[10rem] truncate text-sm text-muted-foreground"
        title={user.email}
      >
        {truncateEmail(user.email)}
      </span>
      <Button variant="outline" size="sm" onClick={logout}>
        Cerrar sesión
      </Button>
    </div>
  );
}
