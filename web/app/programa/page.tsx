import { Suspense } from "react";

import { ProgramaSection } from "@/components/programa/programa-section";
import { ProgramaSkeleton } from "@/components/programa/programa-skeleton";

export const metadata = {
  title: "Programa",
};

export default function ProgramaPage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-8 px-4 py-10 sm:py-16">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Programa</h1>
        <p className="max-w-2xl text-muted-foreground">
          Cronograma de campeonatos, alertas de tus nadadores seguidos y carga de nuevos
          programas.
        </p>
      </header>

      <Suspense fallback={<ProgramaSkeleton />}>
        <ProgramaSection />
      </Suspense>
    </div>
  );
}
