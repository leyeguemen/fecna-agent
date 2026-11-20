"use client";

import { useId, useState, type FormEvent } from "react";

import { faEnvelope, faLock } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";

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
      <DialogContent className="sm:max-w-sm">
        {/* "login-box" de AdminLTE: logo centrado en peso ligero, mensaje,
         * inputs con icono a la derecha y botón primario en bloque. */}
        <DialogHeader className="items-center text-center">
          <DialogTitle className="text-2xl font-light tracking-tight">
            🏊 <span className="font-bold">FECNA</span> Natación
          </DialogTitle>
          <DialogDescription>
            {mode === "login"
              ? "Inicia sesión para comenzar"
              : "Registra una cuenta nueva"}
          </DialogDescription>
        </DialogHeader>

        <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
          <IconInput
            id={emailId}
            label="Email"
            icon={faEnvelope}
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={submitting}
          />

          <div className="flex flex-col gap-1">
            <IconInput
              id={passwordId}
              label="Contraseña"
              icon={faLock}
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
            <IconInput
              id={confirmId}
              label="Confirmar contraseña"
              icon={faLock}
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              disabled={submitting}
            />
          )}

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          {success && !error && (
            <p className="text-sm text-lte-success">{success}</p>
          )}

          <Button type="submit" disabled={submitting} className="mt-1 w-full">
            {submitting
              ? "Enviando…"
              : mode === "login"
                ? "Iniciar sesión"
                : "Registrarse"}
          </Button>
        </form>

        {mode === "login" ? (
          <button
            type="button"
            className="text-left text-sm text-primary hover:underline"
            onClick={() => switchMode("register")}
          >
            Registrar una cuenta nueva
          </button>
        ) : (
          <button
            type="button"
            className="text-left text-sm text-primary hover:underline"
            onClick={() => switchMode("login")}
          >
            Ya tengo una cuenta
          </button>
        )}
      </DialogContent>
    </Dialog>
  );
}

/** Input con el icono en caja a la derecha, como el "input-group" del login
 * de AdminLTE. La etiqueta queda solo para lectores de pantalla (el diseño
 * original usa placeholders). */
function IconInput({
  id,
  label,
  icon,
  ...props
}: React.ComponentProps<typeof Input> & { label: string; icon: IconDefinition }) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <div className="flex">
        <Input id={id} placeholder={label} className="rounded-r-none" {...props} />
        <span
          aria-hidden="true"
          className="flex w-10 shrink-0 items-center justify-center rounded-r-md border border-l-0 border-input text-muted-foreground"
        >
          <FontAwesomeIcon icon={icon} className="size-3.5" />
        </span>
      </div>
    </div>
  );
}
