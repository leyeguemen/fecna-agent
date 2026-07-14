"use client";

import { useState, type FormEvent } from "react";

import { AuthLayout, Button } from "@adminlte/react";

import { ApiError } from "@/lib/api";
import { useUser } from "@/lib/auth";

type Mode = "login" | "register";

/** Pantalla de autenticación basada en los modelos login/register de
 * AdminLTE React. Es la vista inicial mientras no exista una sesión. */
export function LoginScreen() {
  const { login, register } = useUser();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (mode === "register" && password !== confirm) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password);
      }
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Ocurrió un error inesperado.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  function switchMode(next: Mode) {
    setMode(next);
    setPassword("");
    setConfirm("");
    setError(null);
  }

  return (
    <AuthLayout
      authType={mode}
      logo={
        <>
          <i className="bi bi-water me-2" aria-hidden="true" />
          <b>FECNA</b> Natación
        </>
      }
      logoHref="/"
    >
      <p className={`${mode}-box-msg`}>
        {mode === "login"
          ? "Inicia sesión para comenzar"
          : "Registra una cuenta nueva"}
      </p>

      <form onSubmit={handleSubmit}>
        <div className="input-group mb-3">
          <input
            type="email"
            className="form-control"
            placeholder="Email"
            aria-label="Email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={submitting}
          />
          <div className="input-group-text">
            <span className="bi bi-envelope" aria-hidden="true" />
          </div>
        </div>

        <div className="input-group mb-3">
          <input
            type="password"
            className="form-control"
            placeholder="Contraseña"
            aria-label="Contraseña"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={submitting}
          />
          <div className="input-group-text">
            <span className="bi bi-lock-fill" aria-hidden="true" />
          </div>
        </div>

        {mode === "register" && (
          <div className="input-group mb-3">
            <input
              type="password"
              className="form-control"
              placeholder="Confirmar contraseña"
              aria-label="Confirmar contraseña"
              autoComplete="new-password"
              required
              minLength={8}
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              disabled={submitting}
            />
            <div className="input-group-text">
              <span className="bi bi-lock-fill" aria-hidden="true" />
            </div>
          </div>
        )}

        {error && (
          <div className="alert alert-danger py-2" role="alert">
            {error}
          </div>
        )}

        <Button
          type="submit"
          theme="primary"
          className="w-100 mb-3"
          icon={mode === "login" ? "bi-box-arrow-in-right" : "bi-person-plus"}
          label={
            submitting
              ? "Enviando…"
              : mode === "login"
                ? "Iniciar sesión"
                : "Registrarse"
          }
          disabled={submitting}
        />
      </form>

      <p className="mb-0">
        <button
          type="button"
          className="btn btn-link p-0"
          onClick={() => switchMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login"
            ? "Registrar una cuenta nueva"
            : "Ya tengo una cuenta"}
        </button>
      </p>
    </AuthLayout>
  );
}
