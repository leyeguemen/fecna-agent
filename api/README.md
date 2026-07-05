# API FECNA (FastAPI)

API de solo lectura sobre la base pública anonimizada (`data/fecna_public.db`)
más autenticación/estado (Turso o SQLite local). Ver el contrato completo en
`docs/superpowers/specs/2026-06-21-web-app-demo-design.md`.

## Correr en local

```bash
.venv/bin/pip install -r api/requirements.txt
.venv/bin/uvicorn api.main:app --reload
```

Por defecto usa `data/fecna_public.db` (lectura) y `data/fecna_app.db`
(usuarios/programas, SQLite local). Docs interactivas en
`http://localhost:8000/docs`.

**Ojo:** `api/requirements.txt` trae solo el runtime de la API. Para que `/ask`
resuelva nombres/pruebas (ChromaDB) y funcione la subida de programas en PDF
(`pdfplumber`), instala también el `requirements.txt` de la raíz (que ya trae
ambos con sus pines) — es lo normal si desarrollas todo el proyecto en el mismo
venv. En la imagen Docker esto no aplica: `api/requirements-docker.txt` ya los
incluye.

## Variables de entorno

| Variable               | Uso                                                                 | Default                 |
|-------------------------|----------------------------------------------------------------------|--------------------------|
| `FECNA_DB`              | Ruta a la base pública de solo lectura (rankings, /ask).             | `data/fecna_public.db`  |
| `FECNA_APP_DB`          | SQLite local de la app (usuarios/programas) cuando no hay Turso.      | `data/fecna_app.db`     |
| `TURSO_DATABASE_URL`    | URL de la base Turso (prod). Si falta, cae a `FECNA_APP_DB`.          | (vacío)                 |
| `TURSO_AUTH_TOKEN`      | Token de Turso (requerido junto con `TURSO_DATABASE_URL`).            | (vacío)                 |
| `FECNA_JWT_SECRET`      | Clave para firmar los tokens JWT (`api/security.py`).                 | valor de desarrollo     |
| `FECNA_ADMIN_EMAIL`     | Email(s) admin (separados por coma) al registrarse.                  | (vacío → todos "user")  |
| `FECNA_CORS_ORIGINS`    | Orígenes permitidos, separados por coma.                             | `*`                     |
| `FECNA_RATELIMIT_OFF`   | `1` para desactivar el rate limit de `/auth/*` y `/ask` (tests/dev).  | (vacío → activado)      |

## Endpoints

Público (lee `data/fecna_public.db`):
- `GET /health` — estado y conteos.
- `GET /catalogs`, `GET /rankings`, `GET /swimmers/search`,
  `GET /swimmers/{id}`, `GET /swimmers/{id}/history`.
- `POST /ask` — chatbot determinístico (`fecna_agent.agent.chat_answer`);
  responde 503 si la búsqueda semántica (ChromaDB) no está disponible.

Programas (lee/escribe la base de la app):
- `GET /competitions`, `GET /competitions/{id}/schedule|clubs|swimmers`.
- Autenticado: `GET/PUT /competitions/{id}/watch`, `GET /competitions/{id}/alerts`.
- Admin: `POST /competitions` (subir PDF), `DELETE /competitions/{id}`.

Autenticación:
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`.

## Despliegue

Ver la sección "API + Web (demo nueva)" en `../DEPLOY.md` (imagen Docker para
Hugging Face Spaces, variables/secrets y creación de la base en Turso).
