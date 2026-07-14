import { Suspense } from "react";

import { ContentHeader } from "@/components/layout/content-header";
import { ProgramaSection } from "@/components/programa/programa-section";
import { ProgramaSkeleton } from "@/components/programa/programa-skeleton";

export const metadata = {
  title: "Programa",
};

export default function ProgramaPage() {
  return (
    <>
      <div className="app-content-header">
        <div className="container-fluid">
          <ContentHeader title="Programa" />
        </div>
      </div>
      <div className="app-content">
        <div className="container-fluid flex flex-col gap-4">
          <p className="max-w-2xl text-sm text-muted-foreground">
            Cronograma de campeonatos, alertas de tus nadadores seguidos y carga de
            nuevos programas.
          </p>

          <Suspense fallback={<ProgramaSkeleton />}>
            <ProgramaSection />
          </Suspense>
        </div>
      </div>
    </>
  );
}
