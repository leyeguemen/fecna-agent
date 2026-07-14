"use client";

import Link from "next/link";
import { useEffect } from "react";

import {
  DashboardLayout,
  type LinkComponent,
  type MenuNode,
} from "@adminlte/react";

import { LoginScreen } from "@/components/auth/login-screen";
import { useUser } from "@/lib/auth";

const MENU_ITEMS: MenuNode[] = [
  { type: "header", text: "MENÚ" },
  {
    type: "item",
    text: "Inicio",
    href: "/",
    icon: "bi-speedometer",
  },
  {
    type: "item",
    text: "Programa",
    href: "/programa",
    icon: "bi-calendar3",
  },
];

const NextLinkAdapter: LinkComponent = ({ href, children, ...props }) => (
  <Link href={href} {...props}>
    {children}
  </Link>
);

/** Layout oficial de AdminLTE React. La barra superior contiene únicamente
 * controles de la aplicación; la navegación vive exclusivamente en el
 * sidebar, que también gestiona su estado responsive desde la librería. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useUser();

  // La versión actual de DashboardLayout permite configurar el usuario pero
  // no expone un callback para "Sign out". Conectamos ese enlace nativo al
  // store de autenticación y conservamos el resto del user-menu de AdminLTE.
  useEffect(() => {
    if (!user) return;

    const signOut = document.querySelector<HTMLAnchorElement>(
      ".fecna-navbar .user-menu .user-footer a:last-child",
    );
    if (!signOut) return;

    signOut.textContent = "Cerrar sesión";
    const handleLogout = (event: MouseEvent) => {
      event.preventDefault();
      logout();
    };
    signOut.addEventListener("click", handleLogout);
    return () => signOut.removeEventListener("click", handleLogout);
  }, [logout, user]);

  if (!user) {
    return <LoginScreen />;
  }

  return (
    <DashboardLayout
      menuItems={MENU_ITEMS}
      logo={
        <>
          <i className="bi bi-water me-2" aria-hidden="true" />
          <span className="fw-light">FECNA Natación</span>
        </>
      }
      logoHref="/"
      linkComponent={NextLinkAdapter}
      sidebarTheme="dark"
      sidebarBreakpoint="lg"
      fixedHeader
      fixedSidebar
      colorModeToggle
      initialColorMode="auto"
      navbarClass="fecna-navbar fecna-authenticated print:hidden"
      user={{
        name: user.email,
        image: "/icons/icon-192.png",
        role: user.role,
      }}
      footer={
        <span className="ms-2">
          FECNA Natación — demo con datos anonimizados.
        </span>
      }
    >
      {children}
    </DashboardLayout>
  );
}
