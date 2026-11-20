"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { CatalogsResponse } from "@/lib/types";

export const ALL_CATEGORIES = "__TODAS__";

const POOL_LABELS: Record<string, string> = {
  LC: "Piscina larga (LC)",
  SC: "Piscina corta (SC)",
};

const GENDER_LABELS: Record<string, string> = {
  M: "Masculino",
  F: "Femenino",
};

export type FilterKey = "event_id" | "pool" | "gender" | "category";

interface RankingFiltersProps {
  catalogs: CatalogsResponse;
  eventId: string;
  pool: string;
  gender: string;
  category: string;
  onChange: (key: FilterKey, value: string | null) => void;
}

export function RankingFilters({
  catalogs,
  eventId,
  pool,
  gender,
  category,
  onChange,
}: RankingFiltersProps) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
      <Select value={eventId} onValueChange={(v) => onChange("event_id", v as string)}>
        <SelectTrigger className="col-span-2 w-full sm:col-span-1 sm:w-56">
          <SelectValue placeholder="Prueba" />
        </SelectTrigger>
        <SelectContent>
          {catalogs.pruebas.map((p) => (
            <SelectItem key={p.id} value={p.id}>
              {p.nombre}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={pool} onValueChange={(v) => onChange("pool", v as string)}>
        <SelectTrigger className="w-full sm:w-44">
          <SelectValue placeholder="Piscina" />
        </SelectTrigger>
        <SelectContent>
          {catalogs.piscinas.map((p) => (
            <SelectItem key={p} value={p}>
              {POOL_LABELS[p] ?? p}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={gender} onValueChange={(v) => onChange("gender", v as string)}>
        <SelectTrigger className="w-full sm:w-36">
          <SelectValue placeholder="Género" />
        </SelectTrigger>
        <SelectContent>
          {catalogs.generos.map((g) => (
            <SelectItem key={g} value={g}>
              {GENDER_LABELS[g] ?? g}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={category || ALL_CATEGORIES}
        onValueChange={(v) => onChange("category", v === ALL_CATEGORIES ? null : (v as string))}
      >
        <SelectTrigger className="w-full sm:w-40">
          <SelectValue placeholder="Categoría" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_CATEGORIES}>Todas</SelectItem>
          {catalogs.categorias.map((c) => (
            <SelectItem key={c.id} value={c.id}>
              {c.nombre}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
