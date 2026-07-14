import { Suspense } from "react";

import { ContentHeader } from "@/components/layout/content-header";
import { ProgramaSection } from "@/components/programa/programa-section";
import { ProgramaSkeleton } from "@/components/programa/programa-skeleton";

export const metadata = {
  title: "Programa",
};

export default function ProgramaPage() {
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-4 sm:px-6 sm:py-6">
      <ContentHeader title="Programa" />
      <p className="max-w-2xl text-sm text-muted-foreground">
        Cronograma de campeonatos, alertas de tus nadadores seguidos y carga de nuevos
        programas.
      </p>

      <Suspense fallback={<ProgramaSkeleton />}>
        <ProgramaSection />
      </Suspense>
    </div>
  );
}
