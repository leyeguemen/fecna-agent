"use client";

import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { Trash2, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { CompetitionSummary, CompetitionUploadResponse } from "@/lib/types";

import { formatUploadStatus, networkAwareMessage } from "./utils";

interface AdminPanelProps {
  /** Campeonato actualmente seleccionado (para el borrado), o `null` si
   * todavía no hay ninguno cargado (p.ej. estado vacío). */
  selected: CompetitionSummary | null;
  onUploaded: (result: CompetitionUploadResponse) => void;
  onDeleted: () => void;
}

type UploadStatus = "idle" | "uploading" | "done" | "error";

/** Sección solo-admin: cargar un programa (PDF) y borrar el campeonato
 * seleccionado. Usa `api.postForm` (multipart) para la carga. */
export function AdminPanel({ selected, onUploaded, onDeleted }: AdminPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [fileName, setFileName] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    setFileName(e.target.files?.[0]?.name ?? null);
    setUploadStatus("idle");
    setUploadMessage(null);
  }

  async function handleUpload(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    const file = fileInputRef.current?.files?.[0];
    if (!token || !file) return;

    setUploadStatus("uploading");
    setUploadMessage(null);

    const form = new FormData();
    form.append("file", file);

    try {
      const result = await api.postForm<CompetitionUploadResponse>("/competitions", form, token);
      setUploadStatus("done");
      setUploadMessage(
        `Programa ${formatUploadStatus(result.status)} · ${result.entradas} inscripciones · ${result.cruzados} cruzados`,
      );
      onUploaded(result);
      setFileName(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setUploadStatus("error");
      setUploadMessage(networkAwareMessage(err, "No se pudo cargar el programa."));
    }
  }

  async function handleDelete() {
    if (!selected) return;
    const token = getToken();
    if (!token) return;

    setDeleting(true);
    setDeleteError(null);
    try {
      await api.delete<void>(`/competitions/${selected.id}`, token);
      setConfirmOpen(false);
      onDeleted();
    } catch (err) {
      setDeleteError(networkAwareMessage(err, "No se pudo eliminar el campeonato."));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-border/60 p-4">
      <h2 className="text-sm font-semibold tracking-tight text-muted-foreground">
        Administración
      </h2>

      <form className="flex flex-col gap-2 sm:flex-row sm:items-center" onSubmit={handleUpload}>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          onChange={handleFileChange}
          disabled={uploadStatus === "uploading"}
          className="flex-1 text-sm text-muted-foreground file:mr-2 file:rounded-lg file:border file:border-input file:bg-transparent file:px-2.5 file:py-1 file:text-sm file:font-medium file:text-foreground"
        />
        <Button type="submit" size="sm" disabled={!fileName || uploadStatus === "uploading"}>
          <Upload data-icon="inline-start" />
          {uploadStatus === "uploading" ? "Cargando…" : "Cargar programa (PDF)"}
        </Button>
      </form>

      {uploadStatus === "done" && uploadMessage && (
        <p className="text-sm text-emerald-600 dark:text-emerald-400">{uploadMessage}</p>
      )}
      {uploadStatus === "error" && uploadMessage && (
        <p role="alert" className="text-sm text-destructive">
          {uploadMessage}
        </p>
      )}

      {selected && (
        <div className="flex items-center justify-between gap-3 border-t border-border/60 pt-3">
          <p className="text-sm text-muted-foreground">
            Eliminar «{selected.name}» del programa (no afecta rankings ni fichas).
          </p>
          <Button variant="destructive" size="sm" onClick={() => setConfirmOpen(true)}>
            <Trash2 data-icon="inline-start" />
            Eliminar
          </Button>
        </div>
      )}

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar campeonato</DialogTitle>
            <DialogDescription>
              ¿Eliminar «{selected?.name}»? Se borrará su cronograma y las alertas asociadas.
              Esta acción no se puede deshacer.
            </DialogDescription>
          </DialogHeader>

          {deleteError && (
            <p role="alert" className="text-sm text-destructive">
              {deleteError}
            </p>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)} disabled={deleting}>
              Cancelar
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting ? "Eliminando…" : "Eliminar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
