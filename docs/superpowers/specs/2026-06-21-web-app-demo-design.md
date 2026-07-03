# Diseño: Web app demo (FastAPI + Next.js)

Fecha: 2026-06-21 · Rama: `feature/web-app` (develop queda intacto; el Streamlit
actual sigue funcionando y desplegado durante toda la migración).

## Objetivo
Una interfaz web moderna y agradable en desktop y móvil, desplegable **gratis**,
que sirva como demo vendible. Si luego se cobra, solo se mueve el hosting del
backend a un plan pago; el resto no cambia.

## Decisiones (aprobadas por el usuario)
- **Backend:** FastAPI (Python) exponiendo la lógica existente de `fecna_agent/`
  como API REST. Deploy gratis en **Hugging Face Spaces (Docker)** (no se duerme
  a los 15 min como Render free; 2 vCPU/16GB).
- **Frontend:** **Next.js (React + TypeScript)** con Tailwind CSS + shadcn/ui,
  deploy gratis en **Vercel**. Mobile-first, instalable como **PWA**.
- **Acceso:** público para consultar (ranking, fichas — datos anonimizados, es
  el escaparate); **login solo para acciones**: seguir nadadores/alertas (user)
  y cargar/borrar programas (admin). Registro abierto. Roles como en Streamlit
  (`FECNA_ADMIN_EMAIL`).
- **Datos divididos en dos bases:**
  - **Lectura (rankings, catálogos):** SQLite anonimizada **embebida** en la
    imagen del backend (read-only). Se actualiza con push, igual que hoy — el
    sync es local de todas formas (anti-bot).
  - **Escritura (cuentas, programas, seguidos):** **Turso** (libSQL, SQLite
    gestionado, free tier 9GB). Persiste entre despliegues → resuelve el
    pendiente de Fase 2 del login y el de persistencia del programa.
- **Alcance de la demo (Fase B):** 3 páginas — Inicio+Ranking, Ficha,
  Programa/Alertas. El resto (comparar, chatbot, novedades, evolución) queda
  planificado como Fase C sobre la misma base.
- **Chatbot:** el endpoint del agente se expone desde el día 1 (barato); la
  pantalla de chat es Fase C.

## Arquitectura

```
web/   Next.js (Vercel)  ──HTTPS──▶  api/  FastAPI (HF Spaces, Docker)
                                       │
                        ┌──────────────┴──────────────┐
                 data/fecna_public.db          Turso (libSQL)
                 (read-only, embebida)         app_user, competition,
                 rankings + catálogos          competition_entry/watch
                                       │
                                 fecna_agent/  (lógica actual, sin reescribir)
```

- Monorepo: carpetas nuevas `api/` y `web/` junto a lo existente. `app.py` y
  `pages/` (Streamlit) no se tocan en esta rama.
- `api/` importa `fecna_agent` directamente (mismo repo, mismo paquete).
- CORS: la API permite el origen del front (env `FECNA_CORS_ORIGINS`).

## Doble conexión de base
Las funciones de `db.py` ya reciben `conn` como primer argumento — no se
reescriben. La API abre dos conexiones y pasa la que corresponde:
- `read_conn()` → SQLite local embebida (rankings, catálogos, nadadores).
- `app_conn()` → Turso vía el cliente `libsql` (API compatible con sqlite3).
  - Env: `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`.
  - **Fallback dev:** sin esas variables, usa un archivo local
    (`data/fecna_app.db`) — desarrollo y tests no requieren Turso.
- Las tablas de escritura (`app_user`, `competition*`) se crean en Turso con el
  mismo SCHEMA (el `connect()` actual ya es idempotente con
  `CREATE TABLE IF NOT EXISTS`).

## Autenticación (JWT)
- Reusa `fecna_agent/auth.py` (pbkdf2, validaciones, roles) tal cual.
- `POST /auth/register` y `POST /auth/login` → access token **JWT** (PyJWT),
  claims: `sub` (user id), `email`, `role`; expiración 7 días (demo).
- Secreto: env `FECNA_JWT_SECRET` (obligatorio en prod; en dev se genera).
- Dependencia FastAPI `current_user` (token → usuario) y `require_admin`.
- El front guarda el token (localStorage) y lo envía como `Bearer`.

## Fases
- **Fase A:** la API (este contrato) + auth JWT + doble base. Se prueba sola
  (pytest/curl) antes de escribir una línea del front.
- **Fase B:** el front demo (3 páginas) consumiendo la API.
- **Fase C:** backlog post-demo (ver abajo).

## Contrato de la API (v1) — Fase A
Público (lee la base embebida):
- `GET /health` — estado y conteos.
- `GET /catalogs` — pruebas, categorías, ligas, piscinas.
- `GET /rankings?event_id&pool&gender&category&limit` — ranking filtrado.
- `GET /swimmers/search?q=` — buscar nadador por nombre.
- `GET /swimmers/{id}` — ficha: datos + mejores pruebas + puestos.
- `GET /swimmers/{id}/history?event_id&pool` — evolución.
- `GET /competitions` y `GET /competitions/{id}/schedule?club&swimmer` —
  programas cargados y cronograma.
- `POST /ask` — chatbot (agente determinístico); pantalla en Fase C.

Autenticado (Turso):
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`.
- `GET/PUT /competitions/{id}/watch` — nadadores seguidos **por usuario**
  (nueva columna `user_id` en `competition_watch`; en Streamlit era global).
- Admin: `POST /competitions` (subir PDF del programa, multipart) y
  `DELETE /competitions/{id}`.

## Frontend (Fase B — la demo)
- Next.js App Router + TypeScript + Tailwind + shadcn/ui. Diseño mobile-first,
  tema claro/oscuro, español.
- Páginas:
  1. **Inicio/Ranking** (`/`): buscador de nadador + ranking con filtros
     (prueba, piscina, género, categoría). Tabla responsiva (cards en móvil).
  2. **Ficha** (`/nadador/[id]`): la infografía como componente React
     (medallas, mejores pruebas, puestos); compartir por link y **print CSS**
     para PDF. (El PNG server-side con Playwright queda para Fase C si hace
     falta.)
  3. **Programa/Alertas** (`/programa`): selector de campeonato, cronograma
     filtrable, seguir nadadores (login), vista "mis alertas" con próxima
     prueba y cuenta regresiva (refresco client-side, trivial en React).
- Auth UI: modal de login/registro; header muestra sesión/cerrar.
- PWA: manifest + íconos (instalable en el celular).

## Fase C (post-demo, misma base — backlog planificado)
comparar, chatbot (con streaming), novedades, evolución (gráfica), rankings del
nadador, PNG server-side de la ficha, pasarela de pago (Wompi/MercadoPago) para
la suscripción de ficha (feature ya documentada).

## Despliegue
- **API:** `api/Dockerfile` (instala requirements + copia `fecna_agent/`,
  `api/` y `data/fecna_public.db`). HF Spaces (SDK Docker). Secrets del Space:
  `TURSO_*`, `FECNA_JWT_SECRET`, `FECNA_ADMIN_EMAIL`, `FECNA_CORS_ORIGINS`.
- **Web:** Vercel apuntando a `web/`; env `NEXT_PUBLIC_API_URL`.
- **Streamlit actual:** intacto en su despliegue mientras tanto.

## Seguridad y privacidad
- La API **solo** embebe la base anonimizada (`fecna_public.db`); la cruda
  jamás sale de local. `app_user` vive en Turso (privado), nunca en el repo.
- Sin secretos en el repo: todos por env/secrets del hosting.
- Rate limiting básico en `/auth/*` (slowapi) para el registro abierto.

## Pruebas
- API: pytest + httpx `TestClient` — auth (register/login/me/roles), rankings
  con filtros, watch por usuario, upload de programa (con PDF de prueba
  sintético). El fallback local de Turso permite correr todo sin red.
- Web: build + type-check como gate mínimo; pruebas e2e quedan para Fase C.

## Fuera de alcance
Reescribir `fecna_agent/`, tocar el Streamlit, apps nativas, pagos (solo queda
la identidad lista), y el sync desde la nube (sigue siendo local).
