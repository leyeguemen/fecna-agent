"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";

const STORAGE_KEY = "fecna-theme";

type Theme = "light" | "dark";

const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((listener) => listener());
}

function subscribe(callback: () => void) {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

function readTheme(): Theme {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "dark" || stored === "light") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

// Snapshot estable para el render en servidor (no hay window ahí). El script
// inline en app/layout.tsx ya aplica la clase "dark" en <html> antes de
// hidratar, así que el único efecto visible de este valor por defecto es el
// ícono durante el primer paint del cliente, que useSyncExternalStore
// corrige solo apenas hidrata (sin el salto de estado de un setState en
// efecto).
function getServerSnapshot(): Theme {
  return "light";
}

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, readTheme, getServerSnapshot);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    window.localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
    notify();
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label="Cambiar tema claro/oscuro"
      onClick={toggle}
    >
      {theme === "dark" ? (
        <Moon className="size-4" />
      ) : (
        <Sun className="size-4" />
      )}
    </Button>
  );
}
