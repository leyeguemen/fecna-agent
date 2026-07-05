"use client";

import { useId, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { useUser } from "@/lib/auth";
import { cn } from "@/lib/utils";

type Mode = "login" | "register";

interface AuthDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Modo inicial al abrir el diálogo (por defecto "login"). */
  defaultMode?: Mode;
}

const PASSWORD_HINT = "Mínimo 8 caracteres, con letra y número.";

export function AuthDialog({ open, onOpenChange, defaultMode = "login" }: AuthDialogProps) {
  const { login, register } = useUser();
  const emailId = useId();
  const passwordId = useId();
  const confirmId = useId();

  const [mode, setMode] = useState<Mode>(defaultMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  function resetFields() {
    setEmail("");
    setPassword("");
    setConfirm("");
    setError(null);
    setSuccess(null);
  }

  function switchMode(next: Mode) {
    setMode(next);
    setError(null);
  }

  function handleOpenChange(next: boolean) {
    if (!next) resetFields();
    onOpenChange(next);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (mode === "register" && password !== confirm) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
        setSuccess("Sesión iniciada.");
      } else {
        await register(email, password);
        setSuccess("Cuenta creada.");
      }
      setPassword("");
      setConfirm("");
      // Cierre con una pequeña pausa para que se note el feedback de éxito.
      window.setTimeout(() => handleOpenChange(false), 500);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Ocurrió un error inesperado.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {mode === "login" ? "Iniciar sesión" : "Registrarse"}
          </DialogTitle>
          <DialogDescription>
            {mode === "login"
              ? "Ingresa con tu email y contraseña."
              : "Crea una cuenta con tu email y una contraseña."}
          </DialogDescription>
        </DialogHeader>

        <div className="flex gap-1 rounded-lg bg-muted p-1 text-sm">
          <button
            type="button"
            className={cn(
              "flex-1 rounded-md px-2.5 py-1.5 font-medium transition-colors",
              mode === "login"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
            onClick={() => switchMode("login")}
          >
            Iniciar sesión
          </button>
          <button
            type="button"
            className={cn(
              "flex-1 rounded-md px-2.5 py-1.5 font-medium transition-colors",
              mode === "register"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
            onClick={() => switchMode("register")}
          >
            Registrarse
          </button>
        </div>

        <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-1">
            <label htmlFor={emailId} className="text-sm font-medium">
              Email
            </label>
            <Input
              id={emailId}
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={submitting}
            />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor={passwordId} className="text-sm font-medium">
              Contraseña
            </label>
            <Input
              id={passwordId}
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={submitting}
            />
            {mode === "register" && (
              <p className="text-xs text-muted-foreground">{PASSWORD_HINT}</p>
            )}
          </div>

          {mode === "register" && (
            <div className="flex flex-col gap-1">
              <label htmlFor={confirmId} className="text-sm font-medium">
                Confirmar contraseña
              </label>
              <Input
                id={confirmId}
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                disabled={submitting}
              />
            </div>
          )}

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          {success && !error && (
            <p className="text-sm text-emerald-600 dark:text-emerald-400">{success}</p>
          )}

          <Button type="submit" disabled={submitting} className="mt-1 w-full">
            {submitting
              ? "Enviando…"
              : mode === "login"
                ? "Iniciar sesión"
                : "Crear cuenta"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
