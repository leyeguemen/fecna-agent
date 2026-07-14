import type { Metadata } from "next";

import { FichaBuilder } from "@/components/ficha/ficha-builder";
import { api } from "@/lib/api";
import type { SwimmerOptionsResponse, SwimmerProfile } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Ficha",
  description: "Ficha visual, mejores marcas y posiciones de un nadador FECNA.",
};

interface PageProps {
  searchParams: Promise<{ swimmer_id?: string }>;
}

export default async function FichaPage({ searchParams }: PageProps) {
  const { swimmer_id: requestedId } = await searchParams;
  const options = await api.get<SwimmerOptionsResponse>("/swimmers/options");
  const selected = options.items.find((item) => item.swimmer_id === requestedId) ?? options.items[0];

  if (!selected) {
    return (
      <div className="app-content">
        <div className="container-fluid py-4">
          <h1 className="h3">🪪 Ficha</h1>
          <div className="alert alert-info mt-3" role="status">
            No hay nadadores disponibles para generar una ficha.
          </div>
        </div>
      </div>
    );
  }

  const profile = await api.get<SwimmerProfile>(`/swimmers/${selected.swimmer_id}`);

  return (
    <div className="app-content">
      <div className="container-fluid">
        <FichaBuilder initialProfile={profile} selectionMode="same-page" />
      </div>
    </div>
  );
}
