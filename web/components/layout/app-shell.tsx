"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import {
  faBars,
  faCalendarDays,
  faGaugeHigh,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { SessionButton } from "@/components/session-button";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

/**
 * Shell de la app al estilo AdminLTE 3: sidebar oscuro fijo a la izquierda,
 * navbar superior clara, contenido gris y footer. En móvil el sidebar es un
 * panel deslizante (off-canvas) con overlay, abierto por la hamburguesa.
 */

const NAV_ITEMS = [
  { href: "/", label: "Inicio", icon: faGaugeHigh },
  { href: "/programa", label: "Programa", icon: faCalendarDays },
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
                    <FontAwesomeIcon icon={item.icon} className="h-4 w-4 shrink-0" fixedWidth />
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
              <FontAwesomeIcon icon={faBars} className="h-5 w-5" />
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
