"use client";

import { useEffect } from "react";

/** Carga los plugins interactivos de Bootstrap solo en el navegador.
 * AdminLTE React usa data-bs-toggle para sus dropdowns de usuario y tema. */
export function BootstrapClient() {
  useEffect(() => {
    void import("bootstrap");
  }, []);

  return null;
}
