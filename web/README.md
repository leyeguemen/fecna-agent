# FECNA Natación — Web (demo)

Frontend de la demo (Fase B): Next.js (App Router) + TypeScript + Tailwind +
shadcn/ui, consumiendo la API FastAPI (`api/`) de solo lectura + auth.

## Requisitos

- Node 20 (fijado en `.nvmrc`; con `nvm use` en este directorio basta).
- La API corriendo en local (ver `../api/README.md`).

## Correr en local

1. API (desde la raíz del repo, en otra terminal):

   ```bash
   .venv/bin/uvicorn api.main:app --reload
   ```

   Por defecto queda en `http://localhost:8000`.

2. Front (desde `web/`):

   ```bash
   nvm use          # o: export PATH="$HOME/.nvm/versions/node/v20.20.2/bin:$PATH"
   npm install
   npm run dev
   ```

   Abre `http://localhost:3000`.

## Variables de entorno

| Variable                | Uso                                  | Default                 |
|--------------------------|----------------------------------------|--------------------------|
| `NEXT_PUBLIC_API_URL`   | Base URL de la API (`web/lib/api.ts`). | `http://localhost:8000` |

Para apuntar a otra API, crea `web/.env.local`:

```
NEXT_PUBLIC_API_URL=https://mi-api.example.com
```

## Build / gate

```bash
npm run build      # next build — debe compilar sin errores
npx tsc --noEmit   # type-check estricto, sin emitir
npm run lint       # eslint (next/core-web-vitals + next/typescript)
```

## Estructura

- `app/` — rutas (App Router), sin `src/`. Alias de imports `@/*` → raíz de `web/`.
- `lib/types.ts` — tipos del contrato de la API (leídos de `api/routers/*.py`, no inventados).
- `lib/api.ts` — cliente fetch tipado (`api.get/post/put/delete`), usa `NEXT_PUBLIC_API_URL`, lanza `ApiError { status, detail }` con el `detail` que devuelve FastAPI.
- `components/ui/` — primitivas shadcn/ui (`button`, `input`, `card`, `dialog`, `select`, `table`) generadas con `npx shadcn@latest add ...`. Estilo `base-nova`, tema con variables CSS en `app/globals.css`.
- `components/site-header.tsx`, `components/site-footer.tsx`, `components/theme-toggle.tsx`, `components/session-button.tsx` — layout base. El botón de sesión es un placeholder deshabilitado; la tarea B2 lo conecta a `/auth/*`.
- `app/manifest.ts` + `public/icons/*.png` + `app/icon.png` / `app/apple-icon.png` — PWA (manifest, favicon, ícono iOS).

## Decisiones de scaffold

- `create-next-app@latest web` con `--typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*"`: App Router en `web/app/` (sin `src/`), Tailwind v4 (config vía CSS, no `tailwind.config.js`).
- shadcn/ui instalado con el CLI (`npx shadcn@latest init -d -y` + `add input card dialog select table`), preset `base-nova`. El CLI generó `components.json`, `components/ui/*` y ajustó `app/globals.css` (variables de tema OKLCH, `@custom-variant dark (&:is(.dark *))` — habilita el toggle por clase `.dark` en `<html>`).
- Tema claro/oscuro: clase `.dark` en `<html>`, toggle en `components/theme-toggle.tsx` persistido en `localStorage` (`fecna-theme`); por defecto sigue `prefers-color-scheme`. Un script inline (`next/script`, `strategy="beforeInteractive"`) en `app/layout.tsx` aplica la clase antes de hidratar para evitar parpadeo.
- Fuentes: `next/font/google` (Geist/Geist Mono) con la variable renombrada a `--font-sans` para que calce con el token de Tailwind que genera shadcn (`app/globals.css: --font-sans: var(--font-sans)`); si se deja el nombre por defecto de `create-next-app` (`--font-geist-sans`) esa referencia queda circular y el tema no aplica la fuente.
- Se eliminaron los archivos boilerplate de `create-next-app` no usados: `AGENTS.md`/`CLAUDE.md` (notas genéricas del propio scaffolder) y los SVG placeholder de `public/` (`next.svg`, `vercel.svg`, etc.), y el `favicon.ico` por defecto (reemplazado por `app/icon.png`).
- Íconos PWA: generados a partir de un SVG (emoji 🏊 sobre fondo sólido `#0369a1`) rasterizado con `sips` (macOS) a los tamaños requeridos — placeholder documentado para reemplazar por artwork real más adelante. Para regenerarlos ver el historial de la tarea B1 o simplemente reemplazar los PNG en `public/icons/` y `app/icon.png` / `app/apple-icon.png` manteniendo los mismos tamaños (192, 512, 512 maskable, 180).
- `/programa` tiene una página placeholder mínima (evita un 404 desde el link del header); el contenido real (selector de campeonato, cronograma, alertas) es de una tarea posterior.
