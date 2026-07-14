"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { SessionButton } from "@/components/session-button";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

/**
 * Shell de la app al estilo AdminLTE 3: sidebar oscuro fijo a la izquierda,
 * navbar superior clara, contenido gris y footer. En móvil el sidebar es un
 * panel deslizante (off-canvas) con overlay, abierto por la hamburguesa.
 */

const NAV_ITEMS = [
  { href: "/", label: "Inicio", icon: HomeIcon },
  { href: "/programa", label: "Programa", icon: CalendarIcon },
] as const;

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    // La ficha (/nadador/…) se llega desde el ranking del inicio.
    return pathname === "/" || pathname.startsWith("/nadador");
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return (
    <div className="min-h-screen">
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          aria-hidden="true"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-sidebar text-sidebar-foreground shadow-lg transition-transform duration-200 lg:translate-x-0 print:hidden",
          open ? "translate-x-0" : "-translate-x-full",
        )}
        aria-label="Menú lateral"
      >
        <Link
          href="/"
          onClick={() => setOpen(false)}
          className="flex h-14 shrink-0 items-center gap-2 border-b border-sidebar-border px-4 font-semibold tracking-tight text-white"
        >
          <span aria-hidden="true" className="text-xl leading-none">
            🏊
          </span>
          <span>FECNA Natación</span>
        </Link>

        <nav aria-label="Principal" className="flex-1 overflow-y-auto px-3 py-4">
          <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/50">
            Menú
          </p>
          <ul className="flex flex-col gap-1">
            {NAV_ITEMS.map((item) => {
              const active = isActive(pathname, item.href);
              const Icon = item.icon;
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={() => setOpen(false)}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors",
                      active
                        ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-sm"
                        : "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span>{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <p className="border-t border-sidebar-border px-4 py-3 text-xs text-sidebar-foreground/50">
          Demo con datos anonimizados
        </p>
      </aside>

      <div className="flex min-h-screen flex-col lg:pl-64 print:pl-0">
        <header className="sticky top-0 z-30 border-b border-border bg-card print:hidden">
          <div className="flex h-14 items-center gap-2 px-4 sm:px-6">
            <button
              type="button"
              className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground lg:hidden"
              aria-label="Abrir menú"
              onClick={() => setOpen(true)}
            >
              <MenuIcon className="h-5 w-5" />
            </button>

            <nav aria-label="Secundaria" className="hidden items-center gap-1 text-sm lg:flex">
              {NAV_ITEMS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-md px-3 py-2 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                >
                  {item.label}
                </Link>
              ))}
            </nav>

            <div className="ml-auto flex items-center gap-2">
              <ThemeToggle />
              <SessionButton />
            </div>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="border-t border-border bg-card px-4 py-3 text-sm text-muted-foreground sm:px-6 print:hidden">
          <span className="font-semibold text-foreground">FECNA Natación</span> — demo con
          datos anonimizados, con fines demostrativos.
        </footer>
      </div>
    </div>
  );
}

// Iconos inline (trazos estilo lucide) para no sumar dependencias.
function HomeIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  );
}

function CalendarIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}

function MenuIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <line x1="4" y1="6" x2="20" y2="6" />
      <line x1="4" y1="12" x2="20" y2="12" />
      <line x1="4" y1="18" x2="20" y2="18" />
    </svg>
  );
}
