"use client";

import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import { Download, FileCode2, FileText, ImageIcon, Upload } from "lucide-react";
import { toPng } from "html-to-image";

import { FichaInfografia, type FichaCustomization } from "@/components/ficha/ficha-infografia";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";
import type { SwimmerOptionsResponse, SwimmerProfile } from "@/lib/types";

const DEFAULT_FROM = "2024-01-01";

function todayIso(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

function slugify(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-zA-Z0-9]+/g, "_").toLowerCase();
}

function download(data: string, filename: string) {
  const anchor = document.createElement("a");
  anchor.href = data;
  anchor.download = filename;
  anchor.click();
}

function readImage(file: File | undefined, setter: (value: string | null) => void) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => setter(typeof reader.result === "string" ? reader.result : null);
  reader.readAsDataURL(file);
}

export function FichaBuilder({ initialProfile }: { initialProfile: SwimmerProfile }) {
  const router = useRouter();
  const cardRef = useRef<HTMLDivElement>(null);
  const [profile, setProfile] = useState(initialProfile);
  const [options, setOptions] = useState<SwimmerOptionsResponse>({ leagues: [], items: [] });
  const [league, setLeague] = useState("");
  const [pool, setPool] = useState("");
  const [dateFrom, setDateFrom] = useState(DEFAULT_FROM);
  const [dateTo, setDateTo] = useState(todayIso);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [customization, setCustomization] = useState<FichaCustomization>({
    photo: null,
    logo: null,
    championship: "",
    venue: "",
  });

  useEffect(() => {
    const query = league ? `?league=${encodeURIComponent(league)}` : "";
    api.get<SwimmerOptionsResponse>(`/swimmers/options${query}`).then(setOptions).catch(() => {
      setMessage("No fue posible cargar la lista de nadadores.");
    });
  }, [league]);

  useEffect(() => {
    if (dateFrom && dateTo && dateFrom > dateTo) {
      return;
    }
    const timer = window.setTimeout(async () => {
      const query = new URLSearchParams();
      if (pool) query.set("pool", pool);
      if (dateFrom) query.set("date_from", dateFrom);
      if (dateTo) query.set("date_to", dateTo);
      setLoading(true);
      setMessage(null);
      try {
        const next = await api.get<SwimmerProfile>(`/swimmers/${profile.swimmer_id}?${query}`);
        setProfile(next);
        if (next.top_events.length === 0) setMessage("No hay pruebas en la piscina seleccionada.");
      } catch (error) {
        setMessage(
          error instanceof ApiError && error.status === 404
            ? "Ese nadador no tiene marcas en el rango seleccionado."
            : error instanceof ApiError
              ? error.detail
              : "No se pudo actualizar la ficha.",
        );
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => window.clearTimeout(timer);
  }, [dateFrom, dateTo, pool, profile.swimmer_id]);

  const invalidDateRange = Boolean(dateFrom && dateTo && dateFrom > dateTo);
  const visibleMessage = invalidDateRange
    ? "La fecha inicial no puede ser posterior a la fecha final."
    : message;

  function updateText(field: "championship" | "venue", value: string) {
    setCustomization((current) => ({ ...current, [field]: value }));
  }

  function handleImage(field: "photo" | "logo", event: ChangeEvent<HTMLInputElement>) {
    readImage(event.target.files?.[0], (value) =>
      setCustomization((current) => ({ ...current, [field]: value })),
    );
  }

  async function handlePng() {
    if (!cardRef.current) return;
    setMessage(null);
    try {
      const dataUrl = await toPng(cardRef.current, { pixelRatio: 2, cacheBust: true, backgroundColor: "#0b2447" });
      download(dataUrl, `ficha_${slugify(profile.swimmer_name)}.png`);
    } catch {
      setMessage("No fue posible generar el PNG en este navegador.");
    }
  }

  function handleHtml() {
    if (!cardRef.current) return;
    const styles = Array.from(document.styleSheets).map((sheet) => {
      try { return Array.from(sheet.cssRules).map((rule) => rule.cssText).join("\n"); } catch { return ""; }
    }).join("\n");
    const html = `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><style>${styles}</style></head><body>${cardRef.current.outerHTML}</body></html>`;
    const url = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
    download(url, `ficha_${slugify(profile.swimmer_name)}.html`);
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <div className="ficha-page">
      <h1 className="ficha-page-title print:hidden"><span aria-hidden="true">🪪</span> Ficha</h1>
      <section className="ficha-controls print:hidden" aria-label="Opciones de la ficha">
        <div className="ficha-control ficha-control-half">
          <label htmlFor="ficha-league">Liga (para filtrar la lista de nadadores)</label>
          <select id="ficha-league" value={league} onChange={(event) => setLeague(event.target.value)}>
            <option value="">Todas</option>
            {options.leagues.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </div>
        <div className="ficha-control ficha-control-half">
          <label htmlFor="ficha-swimmer">Nadador</label>
          <select
            id="ficha-swimmer"
            value={profile.swimmer_id}
            onChange={(event) => router.push(`/nadador/${event.target.value}`)}
          >
            {!options.items.some((item) => item.swimmer_id === profile.swimmer_id) && (
              <option value={profile.swimmer_id}>{profile.swimmer_name} ({profile.club} · {profile.league})</option>
            )}
            {options.items.map((item) => (
              <option key={item.swimmer_id} value={item.swimmer_id}>
                {item.swimmer_name} ({item.club} · {item.league})
              </option>
            ))}
          </select>
        </div>
        <div className="ficha-control ficha-control-third">
          <label htmlFor="ficha-pool">Piscina</label>
          <select id="ficha-pool" value={pool} onChange={(event) => setPool(event.target.value)}>
            <option value="">Ambas</option><option value="LC">LC</option><option value="SC">SC</option>
          </select>
        </div>
        <div className="ficha-control ficha-control-third">
          <label htmlFor="ficha-from">Desde</label>
          <Input id="ficha-from" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
        </div>
        <div className="ficha-control ficha-control-third">
          <label htmlFor="ficha-to">Hasta</label>
          <Input id="ficha-to" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
        </div>

        <h2>Personalizar la ficha <span>(opcional)</span></h2>
        <FilePicker id="ficha-photo" label="Foto del nadador" onChange={(event) => handleImage("photo", event)} />
        <FilePicker id="ficha-logo" label="Logo del club" onChange={(event) => handleImage("logo", event)} />
        <div className="ficha-control ficha-control-half">
          <label htmlFor="ficha-championship">Campeonato</label>
          <Input id="ficha-championship" placeholder="CAMPEONATO NACIONAL INTERCLUBES 2026" value={customization.championship} onChange={(event) => updateText("championship", event.target.value)} />
        </div>
        <div className="ficha-control ficha-control-half">
          <label htmlFor="ficha-venue">Sede</label>
          <Input id="ficha-venue" placeholder="IBAGUÉ" value={customization.venue} onChange={(event) => updateText("venue", event.target.value)} />
        </div>
        {(loading || visibleMessage) && <p className={visibleMessage ? "ficha-message" : "ficha-loading"}>{loading ? "Actualizando ficha…" : visibleMessage}</p>}
      </section>

      <FichaInfografia profile={profile} customization={customization} cardRef={cardRef} />

      <section className="ficha-downloads print:hidden">
        <h2>Descargar</h2>
        <div>
          <Button variant="outline" size="lg" onClick={() => void handlePng()}><ImageIcon /> PNG (redes)</Button>
          <Button variant="outline" size="lg" onClick={() => window.print()}><FileText /> PDF (imprimir)</Button>
          <Button variant="outline" size="lg" onClick={handleHtml}><FileCode2 /> HTML</Button>
        </div>
        <p><Download aria-hidden="true" /> Los archivos incluyen la personalización visible en la ficha.</p>
      </section>
    </div>
  );
}

function FilePicker({ id, label, onChange }: { id: string; label: string; onChange: (event: ChangeEvent<HTMLInputElement>) => void }) {
  return (
    <div className="ficha-control ficha-control-half">
      <label htmlFor={id}>{label}</label>
      <label className="ficha-file" htmlFor={id}>
        <span><Upload aria-hidden="true" /> Subir</span>
        <small>PNG, JPG · máximo 200 MB</small>
      </label>
      <input id={id} className="sr-only" type="file" accept="image/png,image/jpeg" onChange={onChange} />
    </div>
  );
}
