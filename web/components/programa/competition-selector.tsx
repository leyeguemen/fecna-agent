"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { CompetitionSummary } from "@/lib/types";

interface CompetitionSelectorProps {
  competitions: CompetitionSummary[];
  selected: CompetitionSummary | null;
  onChange: (id: number) => void;
}

const POOL_LABELS: Record<string, string> = {
  LC: "Piscina larga (LC)",
  SC: "Piscina corta (SC)",
};

export function CompetitionSelector({ competitions, selected, onChange }: CompetitionSelectorProps) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <Select
        value={selected ? String(selected.id) : ""}
        onValueChange={(v) => onChange(Number(v))}
      >
        <SelectTrigger className="w-full sm:w-80">
          <SelectValue placeholder="Selecciona un campeonato" />
        </SelectTrigger>
        <SelectContent>
          {competitions.map((c) => (
            <SelectItem key={c.id} value={String(c.id)}>
              {c.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {selected && (
        <p className="text-sm text-muted-foreground">
          {POOL_LABELS[selected.pool_type] ?? selected.pool_type} · {selected.entradas} inscripciones
        </p>
      )}
    </div>
  );
}
