import { cache } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { FichaBuilder } from "@/components/ficha/ficha-builder";
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
    <div className="app-content">
      <div className="container-fluid">
        <FichaBuilder initialProfile={profile} />
      </div>
    </div>
  );
}
