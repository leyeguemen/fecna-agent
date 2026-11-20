# Web app demo (FastAPI + Next.js) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Demo web moderna (desktop+móvil) con despliegue gratis: API FastAPI sobre `fecna_agent` + front Next.js, datos de escritura en Turso.

**Architecture:** Monorepo. `api/` (FastAPI) importa `fecna_agent/` sin reescribirlo; dos conexiones (SQLite embebida read-only para rankings, Turso/libSQL para cuentas-programas-seguidos). `web/` (Next.js+TS+Tailwind+shadcn) consume la API. Streamlit intacto.

**Tech Stack:** FastAPI, PyJWT, libsql, pytest+httpx; Next.js (App Router), TypeScript, Tailwind, shadcn/ui; HF Spaces (Docker) + Vercel + Turso.

**Spec:** `docs/superpowers/specs/2026-06-21-web-app-demo-design.md` (leerlo antes de cada tarea).

## Global Constraints
- Rama `feature/web-app`. **No tocar** `app.py`, `pages/`, ni la lógica de `fecna_agent/` salvo lo que el plan indique explícitamente.
- La API solo embebe/lee `data/fecna_public.db` (anonimizada). La cruda jamás.
- Sin secretos en el repo. Env: `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, `FECNA_JWT_SECRET`, `FECNA_ADMIN_EMAIL`, `FECNA_CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`.
- Sin Turso configurado → fallback automático a `data/fecna_app.db` local (dev/tests corren sin red).
- Contraseñas/roles: reusar `fecna_agent/auth.py` y `db.create_user/authenticate` tal cual.
- UI y mensajes en español. TDD en la API (pytest + TestClient); en el front, build+type-check como gate.
- Commits frecuentes con `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

## FASE A — API

### Task A1: Esqueleto de la API + doble conexión
**Files:** Create `api/__init__.py`, `api/main.py`, `api/deps.py`, `api/requirements.txt`, `tests/api/test_health.py`.
**Produces:**
- `deps.read_conn()` → conexión SQLite a `FECNA_DB` (default `data/fecna_public.db`), read-only.
- `deps.app_conn()` → Turso vía `libsql` si hay `TURSO_DATABASE_URL`; si no, `db.connect("data/fecna_app.db")`. Ambas pasan por el `SCHEMA` idempotente de `db.py`.
- `main.app` (FastAPI) con CORS desde `FECNA_CORS_ORIGINS` (default `*` en dev) y `GET /health` → `{"status":"ok","resultados":N,"nadadores":N}`.
- Steps: test de `/health` con TestClient (RED) → implementar → GREEN → commit.

### Task A2: Auth JWT
**Files:** Create `api/security.py`, `api/routers/auth.py`, `tests/api/test_auth_api.py`. Modify `api/main.py` (include_router).
**Consumes:** `db.create_user/authenticate/get_user_by_email`, `auth.role_for`, `deps.app_conn`.
**Produces:**
- `security.create_token(user) -> str` (PyJWT HS256, claims sub/email/role, exp 7d, secreto `FECNA_JWT_SECRET`).
- `security.current_user` y `security.require_admin` (dependencias FastAPI; 401/403 con mensaje en español).
- `POST /auth/register {email,password}` → 201 + token (rol por `FECNA_ADMIN_EMAIL`); errores de `ValueError` → 400 con el mensaje.
- `POST /auth/login` → token o 401 genérico. `GET /auth/me` → email+rol.
- Tests: registro ok/duplicado/contraseña corta, login ok/mal, me con y sin token, rol admin por env. Rate limit básico (slowapi) en `/auth/*`.

### Task A3: Endpoints de lectura (rankings, nadadores, catálogos)
**Files:** Create `api/routers/rankings.py`, `api/routers/swimmers.py`, `tests/api/test_read_api.py`. Modify `api/main.py`.
**Consumes:** `db.ranking`, `db.swimmer_profile`, `db.history`, `db.list_swimmers`, `db.get_catalog`, `categories.age_range`, `deps.read_conn`.
**Produces:**
- `GET /catalogs`, `GET /rankings` (filtros: event_id, pool, gender, category, limit≤100), `GET /swimmers/search?q=` (por nombre normalizado, máx 20), `GET /swimmers/{id}` (perfil/ficha), `GET /swimmers/{id}/history`.
- Respuestas JSON con tiempos ya formateados (`times.ms_to_time`) además de ms.
- Tests con una base sintética pequeña insertada vía `db.insert_results` en fixture.

### Task A4: Endpoints de programa + seguidos por usuario
**Files:** Create `api/routers/competitions.py`, `tests/api/test_competitions_api.py`. Modify `api/main.py`; Modify `fecna_agent/db.py` (solo: `user_id` en `competition_watch` + migración + funciones `list_watched/set_watched/watched_schedule` reciben `user_id`).
**Consumes:** `programa.parse_pdf/map_event_ids/match_swimmers`, `db.save_competition/list_competitions/competition_schedule/...`, `security.current_user/require_admin`.
**Produces:**
- Público: `GET /competitions`, `GET /competitions/{id}/schedule?club&swimmer`, `GET /competitions/{id}/clubs|swimmers`.
- User: `GET/PUT /competitions/{id}/watch` (lista de nombres seguidos **del usuario del token**).
- Admin: `POST /competitions` (multipart PDF → parse → save; respeta la detección de cambios) y `DELETE /competitions/{id}`.
- OJO compat Streamlit: `pages/programa.py` y `pages/alertas.py` llaman `list_watched/set_watched/watched_schedule` sin user_id → darles default `user_id=None` (comportamiento global actual) para no romper develop al fusionar.
- Tests: watch aislado entre dos usuarios; upload con PDF sintético (generarlo con fpdf2 en el test); delete requiere admin.

### Task A5: Endpoint del agente + Dockerfile + guía de deploy
**Files:** Create `api/routers/ask.py`, `api/Dockerfile`, `api/README.md`, `tests/api/test_ask_api.py`. Modify `api/main.py`, `DEPLOY.md` (sección nueva "API en HF Spaces + Turso").
**Produces:**
- `POST /ask {question, context?}` → `agent.chat_answer` determinístico (`{reply, context}`).
- Dockerfile: python slim, instala `requirements.txt` + `api/requirements.txt`, copia `fecna_agent/ api/ data/fecna_public.db data/chroma/`, expone 7860 (HF), `uvicorn api.main:app`.
- DEPLOY.md: crear el Space (Docker), secrets, crear DB en Turso (`turso db create`), URL/token, y cómo apuntar Vercel.
- Test: `/ask` con pregunta de ranking sobre base sintética responde texto con datos.

**Checkpoint Fase A:** suite completa verde + `curl` manual de los endpoints → revisar antes de Fase B.

---

## FASE B — Front demo (3 páginas)

### Task B1: Scaffold Next.js + design system + cliente API
**Files:** Create `web/` (create-next-app: TS, App Router, Tailwind), `web/lib/api.ts` (fetch tipado con `NEXT_PUBLIC_API_URL`), `web/lib/types.ts` (tipos del contrato v1), layout base (header con logo/nav/sesión, tema claro/oscuro), shadcn/ui inicial, manifest PWA + íconos.
**Gate:** `npm run build` + `tsc --noEmit` limpios. `web/README.md` con cómo correr local (API local + front).

### Task B2: Auth en el front
**Files:** Create `web/components/auth/*` (modal login/registro), `web/lib/auth.ts` (token en localStorage, hook `useUser`), header con sesión/cerrar.
**Consumes:** `/auth/register|login|me`.
**Produces:** `useUser() -> {user, login, register, logout}`; fetch autenticado (`Authorization: Bearer`). Mensajes de error de la API mostrados tal cual (ya vienen en español).

### Task B3: Página Inicio/Ranking (`/`)
**Files:** Create `web/app/page.tsx`, `web/components/ranking/*`.
**Produces:** buscador de nadador (autocomplete → `/swimmers/search`, navega a la ficha) + ranking con filtros (selects desde `/catalogs`), tabla desktop / cards móvil, paginación simple, estados de carga/vacío.

### Task B4: Página Ficha (`/nadador/[id]`)
**Files:** Create `web/app/nadador/[id]/page.tsx`, `web/components/ficha/*`.
**Produces:** infografía React (datos, medallas, mejores pruebas con puesto nacional), botón compartir (copiar link) y **print CSS** (imprimir/guardar PDF desde el navegador). SEO básico (metadata con el nombre).

### Task B5: Página Programa/Alertas (`/programa`)
**Files:** Create `web/app/programa/page.tsx`, `web/components/programa/*`.
**Produces:** selector de campeonato, cronograma filtrable (club/nadador), multiselect "seguir nadadores" (requiere login → abre modal), sección "mis alertas" con próxima prueba + cuenta regresiva (refresco cada 60s client-side). Admin logueado ve upload de PDF y borrar.

### Task B6: Deploy + pulido responsive
**Files:** Modify `DEPLOY.md` (sección Vercel), `web/` ajustes.
**Steps:** deploy API a HF Spaces (manual, guiado), crear DB Turso, deploy front a Vercel con `NEXT_PUBLIC_API_URL`, CORS afinado a dominio real, prueba en móvil real, Lighthouse ≥ 90 en móvil como meta de la demo.

**Checkpoint Fase B:** demo pública funcionando end-to-end → revisión final de toda la rama (code-reviewer) → decidir merge a develop.

---

## FASE C — Backlog post-demo (no detallar aún; una tarea por ítem cuando toque)
1. Chatbot (`/pregunta`) con el endpoint `/ask` + streaming visual.
2. Comparar dos nadadores.
3. Novedades (última sincronización).
4. Evolución con gráfica (recharts).
5. Rankings del nadador (todas sus pruebas).
6. PNG server-side de la ficha (Playwright en el Space) si el print CSS no basta.
7. Pasarela de pago (Wompi/MercadoPago) sobre la identidad ya creada — ver `docs/features/suscripcion-descarga-ficha.md`.
8. Retirar Streamlit del despliegue público (queda como herramienta local de admin/sync).

## Self-Review
- Cobertura del spec: doble base ✅ (A1), JWT+roles ✅ (A2), contrato v1 completo ✅ (A3–A5), 3 páginas ✅ (B3–B5), PWA ✅ (B1), watch por usuario ✅ (A4), deploy gratis documentado ✅ (A5/B6), Fase C = resto de páginas + cobro ✅.
- Compatibilidad: cambio de firma de watch con default `user_id=None` para no romper Streamlit (A4) ✅.
- Sin placeholders: cada tarea nombra archivos, interfaces y pruebas; el código completo se escribe al ejecutar cada tarea con su brief (mismo método que el plan del login).
