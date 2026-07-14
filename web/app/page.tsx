import { Suspense } from "react";

import { faPersonSwimming, faStopwatch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { ContentHeader } from "@/components/layout/content-header";
import { SmallBox } from "@/components/layout/small-box";
import { RankingSection } from "@/components/ranking/ranking-section";
import { RankingSkeleton } from "@/components/ranking/ranking-skeleton";
import { SwimmerSearch } from "@/components/ranking/swimmer-search";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { HealthResponse } from "@/lib/types";

// Las cajas de estadísticas muestran conteos en vivo de la API en cada
// visita (sin esto, el build de Vercel dejaría los números congelados).
export const dynamic = "force-dynamic";

// Conteos para las cajas de estadísticas; si la API no responde, la página
// funciona igual (solo se ocultan las cajas).
async function getHealth(): Promise<HealthResponse | null> {
  try {
    return await api.get<HealthResponse>("/health");
  } catch {
    return null;
  }
}

function count(health: HealthResponse | null, key: string): string | null {
  const value = health?.[key];
  return typeof value === "number" ? value.toLocaleString("es-CO") : null;
}

export default async function HomePage() {
  const health = await getHealth();
  const resultados = count(health, "resultados");
  const nadadores = count(health, "nadadores");

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-4 sm:px-6 sm:py-6">
      <ContentHeader title="Ranking nacional" home />

      {(resultados || nadadores) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {resultados && (
            <SmallBox
              value={resultados}
              label="Resultados oficiales"
              color="info"
              icon={<FontAwesomeIcon icon={faStopwatch} />}
            />
          )}
          {nadadores && (
            <SmallBox
              value={nadadores}
              label="Nadadores en la base"
              color="success"
              icon={<FontAwesomeIcon icon={faPersonSwimming} />}
            />
          )}
        </div>
      )}

      <Card className="border-t-[3px] border-t-lte-info">
        <CardHeader className="border-b">
          <CardTitle>Buscar nadador</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-3 text-sm text-muted-foreground">
            Rankings de natación de Colombia — datos públicos FECNA.
          </p>
          <div className="max-w-md">
            <SwimmerSearch />
          </div>
        </CardContent>
      </Card>

      <Card className="border-t-[3px] border-t-primary">
        <CardHeader className="border-b">
          <CardTitle>Ranking</CardTitle>
        </CardHeader>
        <CardContent>
          <Suspense fallback={<RankingSkeleton />}>
            <RankingSection />
          </Suspense>
        </CardContent>
      </Card>
    </div>
  );
}
