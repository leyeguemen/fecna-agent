import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";

export const metadata = {
  title: "Nadador no encontrado",
};

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 px-4 py-24 text-center">
      <span className="text-4xl" aria-hidden="true">
        🔍
      </span>
      <h1 className="text-xl font-semibold tracking-tight">Nadador no encontrado</h1>
      <p className="text-muted-foreground">
        No encontramos ningún nadador con este identificador. Puede que el enlace esté mal
        escrito o que el nadador no exista en la base de datos.
      </p>
      <Link href="/" className={buttonVariants({ variant: "default" })}>
        Volver al inicio
      </Link>
    </div>
  );
}
