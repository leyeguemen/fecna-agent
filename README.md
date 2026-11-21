# NATIA — Tu asistente de natación

App móvil para consultar en lenguaje natural el ranking de natación de FECNA
(rankings, mejores marcas, evolución de nadadores y programas de campeonatos).

```
App Expo (mobile/) ──HTTPS+JWT──> API FastAPI (api/) ──> Supabase Postgres
                                      │  └─ /ask: Claude con tool use (solo lectura)
                                      └─ /admin/sync ──> GitHub Actions ──> scraper ──> Postgres
```

## Componentes
- `mobile/` — app Expo / React Native (Login, Chat, Ranking, Nadador, Torneos, Admin, Perfil).
- `api/` — FastAPI: auth con roles (usuario/admin), rankings, nadadores, campeonatos, `/ask`, `/me`, `/admin`.
- `fecna_agent/` — núcleo: extractor del sitio de FECNA, normalización, SQL exacto (`db.py`),
  capa Postgres (`pg.py`), agente con Claude (`claude_agent.py`) y MCP de solo lectura (`mcp_server.py`).
- `.github/workflows/sync.yml` — sincronización manual (botón Admin) y semanal.

Regla del proyecto: **SQL/Python calcula, el modelo solo explica**. El chat solo ve la vista
`ranking_public` (sin fecha de nacimiento exacta) y todo SQL libre pasa por `sql_guard.py`.

## Desarrollo local
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # completa DATABASE_URL, ANTHROPIC_API_KEY, FECNA_JWT_SECRET…
uvicorn api.main:app --reload --host 0.0.0.0     # API en :8000 (/docs)
cd mobile && cp .env.example .env && npm install && npx expo start
```
En el teléfono, `EXPO_PUBLIC_API_URL` debe apuntar a la IP de tu Mac (no `localhost`) o a la URL de Render.

## Datos
```bash
python -m fecna_agent sync --inicio 2026-01-01      # scraping → base (DATABASE_URL o data/fecna.db)
python -m fecna_agent.migrate_pg --source data/fecna.db [--dry-run]   # SQLite → Postgres
python -m fecna_agent ranking | best | compare | history | recent | ask   # consultas por CLI
```
Sin `DATABASE_URL` se usa SQLite local (`data/fecna.db`). Respeta el delay entre peticiones
(`--delay`, 0,6 s por defecto) al consultar el sitio de FECNA.

## MCP (opcional, para analizar desde Claude Code)
`.mcp.json` registra un servidor de solo lectura sobre la base local (`python -m fecna_agent.mcp_server`).

## Pruebas
```bash
pytest tests -q                       # suite completa (SQLite, sin red)
pytest tests/test_pg_live.py -q       # humo contra Postgres real (usa DATABASE_URL de .env; solo lectura)
cd mobile && npx tsc --noEmit
```

## Despliegue
Ver [DEPLOY.md](DEPLOY.md) (Render + Supabase + EAS).

## Privacidad
Los datos incluyen nombres y fechas de nacimiento de deportistas, algunos menores. El acceso exige
login, las tablas de Supabase tienen RLS activo y nunca se suben secretos ni la base al repositorio.
