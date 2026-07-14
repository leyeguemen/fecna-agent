import { cache } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { FichaActions } from "@/components/ficha/ficha-actions";
import { ContentHeader } from "@/components/layout/content-header";
import { FichaEvolucion } from "@/components/ficha/ficha-evolucion";
import { FichaInfografia } from "@/components/ficha/ficha-infografia";
import { api, ApiError } from "@/lib/api";
import type { SwimmerProfile } from "@/lib/types";

interface PageProps {
  params: Promise<{ id: string }>;
}

// `cache()` (React) memoiza la llamada por render: `generateMetadata` y el
// componente de página piden el mismo perfil, y así solo golpeamos la API
// una vez por request. `lib/api.ts` usa `fetch` global y una URL absoluta
// (`NEXT_PUBLIC_API_URL`), por lo que funciona igual en servidor y cliente —
// no hace falta un helper aparte para SSR.
const getProfile = cache(async (id: string): Promise<SwimmerProfile> => {
  try {
    return await api.get<SwimmerProfile>(`/swimmers/${id}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound();
    }
    throw err;
  }
});

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const profile = await getProfile(id);
  return {
    title: { absolute: `«${profile.swimmer_name}» — FECNA Natación` },
    description: `Ficha de ${profile.swimmer_name} (${profile.club} · ${profile.league}): mejores tiempos y ranking nacional en FECNA Natación.`,
  };
}

export default async function FichaPage({ params }: PageProps) {
  const { id } = await params;
  const profile = await getProfile(id);

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 px-4 py-4 sm:px-6 sm:py-6 print:max-w-none print:gap-4 print:p-0">
      <ContentHeader title="Ficha del nadador" crumb="Nadador" />
      <FichaActions />
      <FichaInfografia profile={profile} />
      <FichaEvolucion swimmerId={profile.swimmer_id} topEvents={profile.top_events} />
    </div>
  );
}
