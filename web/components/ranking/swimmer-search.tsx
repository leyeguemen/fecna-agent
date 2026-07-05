"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";

import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";
import type { SwimmerSearchItem, SwimmerSearchResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

const MIN_QUERY_LENGTH = 3;
const DEBOUNCE_MS = 300;

type Status = "idle" | "loading" | "error" | "done";

/** Buscador de nadador con autocompletado: debounce 300ms, navega a la
 * ficha del nadador al elegir un resultado (click o Enter). */
export function SwimmerSearch() {
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement>(null);
  const requestIdRef = useRef(0);

  const [query, setQuery] = useState("");
  const [items, setItems] = useState<SwimmerSearchItem[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  useEffect(() => {
    const trimmed = query.trim();

    function resetToIdle() {
      setStatus("idle");
      setItems([]);
      setOpen(false);
    }

    if (trimmed.length < MIN_QUERY_LENGTH) {
      requestIdRef.current += 1;
      resetToIdle();
      return;
    }

    const requestId = ++requestIdRef.current;

    function startLoading() {
      setStatus("loading");
      setErrorMessage(null);
      setOpen(true);
    }
    startLoading();

    const timer = window.setTimeout(() => {
      api
        .get<SwimmerSearchResponse>(`/swimmers/search?q=${encodeURIComponent(trimmed)}`)
        .then((res) => {
          if (requestIdRef.current !== requestId) return;
          setItems(res.items);
          setStatus("done");
          setActiveIndex(-1);
        })
        .catch((err) => {
          if (requestIdRef.current !== requestId) return;
          setItems([]);
          setStatus("error");
          if (err instanceof ApiError && err.kind === "network") {
            setErrorMessage("No se pudo conectar con el servidor.");
          } else if (err instanceof ApiError) {
            setErrorMessage(err.detail);
          } else {
            setErrorMessage("Ocurrió un error inesperado.");
          }
        });
    }, DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function goTo(item: SwimmerSearchItem) {
    setOpen(false);
    router.push(`/nadador/${item.swimmer_id}`);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Escape") {
      setOpen(false);
      return;
    }
    if (!open || items.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => (i + 1) % items.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => (i <= 0 ? items.length - 1 : i - 1));
    } else if (e.key === "Enter") {
      if (activeIndex >= 0 && activeIndex < items.length) {
        e.preventDefault();
        goTo(items[activeIndex]);
      }
    }
  }

  const showDropdown = open && query.trim().length >= MIN_QUERY_LENGTH;

  return (
    <div ref={containerRef} className="relative w-full">
      <Input
        type="search"
        placeholder="Busca un nadador por nombre…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => {
          if (query.trim().length >= MIN_QUERY_LENGTH) setOpen(true);
        }}
        onKeyDown={handleKeyDown}
        role="combobox"
        aria-expanded={showDropdown}
        aria-controls="swimmer-search-listbox"
        aria-autocomplete="list"
        className="h-10 text-base"
      />

      {showDropdown && (
        <div
          id="swimmer-search-listbox"
          role="listbox"
          className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-border bg-popover text-popover-foreground shadow-md"
        >
          {status === "loading" && (
            <p className="px-3 py-2 text-sm text-muted-foreground">Buscando…</p>
          )}
          {status === "error" && (
            <p role="alert" className="px-3 py-2 text-sm text-destructive">
              {errorMessage}
            </p>
          )}
          {status === "done" && items.length === 0 && (
            <p className="px-3 py-2 text-sm text-muted-foreground">Sin resultados.</p>
          )}
          {status === "done" && items.length > 0 && (
            <ul>
              {items.map((item, index) => (
                <li key={item.swimmer_id} role="option" aria-selected={index === activeIndex}>
                  <button
                    type="button"
                    className={cn(
                      "flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left text-sm transition-colors",
                      index === activeIndex
                        ? "bg-accent text-accent-foreground"
                        : "hover:bg-accent hover:text-accent-foreground",
                    )}
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => goTo(item)}
                  >
                    <span className="font-medium">{item.swimmer_name}</span>
                    <span className="text-xs text-muted-foreground">
                      {item.club} · {item.league}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
