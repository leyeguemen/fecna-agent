# Despliegue gratuito (Streamlit Community Cloud)

Guía para publicar la app gratis, en modo **público anonimizado**.

## Cómo queda anonimizado

Para poder publicar sin exponer datos de menores, NO se sube la base cruda. Se
sube una **copia anonimizada**:

- La identificación (cédula) se reemplaza por un pseudónimo estable.
- La fecha de nacimiento se reduce al año (basta para la categoría).
- Nombres, club, liga y tiempos se conservan: son los datos que la federación
  ya publica.

Además la app, en modo público (`FECNA_PUBLIC=1`):

- Oculta la columna de fecha de nacimiento en la tabla de ranking.
- Muestra un código (#XXXXX) en vez de la identificación en los selectores.
- Oculta los controles de extracción/sincronización (queda de solo lectura).

## Pasos

### 1. Generar la base anonimizada

```bash
python -m fecna_agent anonymize        # crea data/fecna_public.db
```

Tu base original (`data/fecna.db`) no se toca y sigue ignorada por git. Solo
`data/fecna_public.db` está permitida en el repo (ver `.gitignore`).

### 2. Subir al repo

```bash
git add -f data/fecna_public.db
git add app.py pages/ requirements.txt packages.txt .gitignore DEPLOY.md README.md fecna_agent/
git commit -m "Despliegue: base anonimizada y modo público"
git push
```

### 3. Desplegar en Streamlit Community Cloud

1. Entra a https://share.streamlit.io e inicia sesión con GitHub.
2. "Create app" → desde el repo `leyeguemen/fecna-agent`, rama **`develop`**,
   archivo `app.py`. (La app desplegada sigue `develop`, no `main`: las nuevas
   funciones llegan al desplegado al hacer push a `develop`.)
3. En **Advanced settings → Secrets**, pega:

   ```toml
   FECNA_PUBLIC = "1"
   FECNA_DB = "data/fecna_public.db"
   ```

   Para **exigir login** (candado total: nadie ve la app sin registrarse),
   añade además:

   ```toml
   FECNA_AUTH = "1"
   FECNA_ADMIN_EMAIL = "tu@correo.com"   # uno o varios, separados por coma
   ```

   Advertencia: con el disco efímero de la nube, **las cuentas se borran en cada
   redeploy** (todos deben volver a registrarse) hasta resolver la persistencia
   externa — ver `docs/features/persistencia-programa-despliegue.md`.

4. "Deploy" (la primera vez tarda unos minutos instalando dependencias).

### 4. Listo

La app queda pública pero anonimizada. Comparte la URL sin exponer cédulas ni
fechas de nacimiento.

## Actualizar los datos más adelante

La sincronización desde la nube falla por el bloqueo anti-bot de ecoapplet.
Actualiza en tu máquina y vuelve a publicar:

```bash
python -m fecna_agent sync             # actualiza data/fecna.db (local)
python -m fecna_agent anonymize        # regenera data/fecna_public.db
git add -f data/fecna_public.db && git commit -m "Datos actualizados" && git push
```

Streamlit redespliega solo al detectar el push **a `develop`** (la rama que
sigue la app). Haz los commits sobre `develop`.

## Descarga de la ficha en PNG/PDF (Playwright)

La página **Ficha** genera PNG (para redes) y PDF (para imprimir) renderizando
el HTML con el Chromium de Playwright. Para que funcione en la nube:

- `requirements.txt` ya incluye `playwright`.
- `packages.txt` ya incluye las librerías del sistema que Chromium necesita
  (libnss3, libgbm1, libasound2, etc.) y `fonts-noto-color-emoji` (medallas a
  color).
- El **build de Streamlit Cloud no corre `playwright install`**, así que la app
  descarga el navegador la **primera vez** que se abre la página de Ficha
  (`fecna_agent/ficha.py::ensure_browser`, cacheado). Esa primera vez tarda ~1
  min; después es inmediato.

Si por algún motivo el navegador no queda disponible, la página sigue
funcionando y ofrece la descarga en **HTML** (que puedes imprimir a PDF o
capturar como imagen desde el navegador). Localmente no hace falta nada: el
Chromium de Playwright ya viene instalado.

## Archivos de despliegue ya preparados

- `requirements.txt` — dependencias + `pysqlite3-binary` (ChromaDB lo necesita
  en Linux) + `playwright` (ficha PNG/PDF).
- `packages.txt` — fuente DejaVu (export PNG de tablas), emojis a color y las
  librerías de Chromium para la ficha.
- `app.py` — host de navegación multipágina (menú con `st.navigation`); el
  código común (modo público `FECNA_PUBLIC`, base `FECNA_DB`, swap de sqlite,
  reconstrucción del índice) está en `fecna_agent/webui.py`.
- `pages/programa.py` — pestaña Programa: carga del heat sheet (PDF) y
  cronograma filtrable por club/nadador. Requiere `pdfplumber` (ya en
  `requirements.txt`). Los programas cargados quedan en las tablas `competition`
  y `competition_entry` de `fecna_public.db` (se generan al correr `anonymize`).

## Notas

- Ollama (IA local) no está disponible en la nube; las respuestas siguen siendo
  determinísticas.
- El sistema de archivos de la nube es efímero: la fuente de verdad es el
  `data/fecna_public.db` del repo.
- Si activas `FECNA_AUTH`, las cuentas se guardan en SQLite y **no sobreviven a
  un redeploy** (disco efímero). Persistirlas requiere una base externa — ver
  `docs/features/persistencia-programa-despliegue.md` (mismo pendiente).

## Alternativa: Hugging Face Spaces

Crea un Space (SDK Streamlit), sube los archivos + `data/fecna_public.db`, y en
*Settings → Variables and secrets* agrega `FECNA_PUBLIC=1` y
`FECNA_DB=data/fecna_public.db`. Mismo `requirements.txt` y `packages.txt`.

## API + Web (demo nueva)

La demo nueva (FastAPI + Next.js, ver
`docs/superpowers/specs/2026-06-21-web-app-demo-design.md`) se despliega aparte
del Streamlit actual, que sigue intacto. Fase A es solo la API; el front
(Vercel) llega en Fase B.

### API en Hugging Face Spaces (SDK: Docker)

1. Crea un Space nuevo → **SDK: Docker**.
2. El Dockerfile de la API vive en `api/Dockerfile` (no en la raíz del repo).
   Dos formas de apuntarlo, según lo que soporte tu Space:
   - Si el Space permite indicar la ruta del Dockerfile en el README (front
     matter `dockerfile: api/Dockerfile`), úsala directamente conectando el
     repo de GitHub.
   - Si no, copia/enlaza `api/Dockerfile` como `Dockerfile` en la raíz del
     repo que subas al Space (el contexto de build sigue siendo la raíz: el
     Dockerfile copia `fecna_agent/`, `api/` y `data/fecna_public.db` con
     rutas relativas a la raíz).
3. El Space expone el puerto **7860** (ya fijado en el Dockerfile con `EXPOSE`
   y `--port 7860`).
4. En *Settings → Variables and secrets* configura:

   | Nombre                | Tipo     | Notas                                        |
   |------------------------|----------|-----------------------------------------------|
   | `TURSO_DATABASE_URL`   | secret   | de `turso db show` (paso siguiente)           |
   | `TURSO_AUTH_TOKEN`     | secret   | de `turso db tokens create`                   |
   | `FECNA_JWT_SECRET`     | secret   | cadena aleatoria larga, propia de este Space  |
   | `FECNA_ADMIN_EMAIL`    | variable | email(s) admin, separados por coma            |
   | `FECNA_CORS_ORIGINS`   | variable | dominio de Vercel cuando exista (Fase B); `*` mientras tanto |

   Sin `TURSO_DATABASE_URL`, la API cae a SQLite local (`data/fecna_app.db`),
   que en Spaces es efímero (se pierde en cada rebuild) — solo sirve para
   probar la imagen, no para producción.
5. El índice semántico (`data/chroma/`, en `.gitignore`) no viaja con el repo:
   la API lo reconstruye sola al arrancar (`api/startup.py`, desde
   `data/fecna_public.db`). Si ChromaDB no está disponible en el Space, la API
   sigue funcionando y `/ask` responde `503`.

### Base de datos en Turso

```bash
turso db create fecna-app
turso db show fecna-app --url          # → TURSO_DATABASE_URL
turso db tokens create fecna-app       # → TURSO_AUTH_TOKEN
```

Pega ambos valores como secrets del Space (paso anterior). El esquema
(`app_user`, `competition`, `competition_watch`, etc.) se crea solo al primer
uso (`fecna_agent.db.SCHEMA`, ejecutado por `api/deps.py::_turso_conn`).

### Web (Fase B)

El front en Next.js se despliega en Vercel apuntando a `web/`, con
`NEXT_PUBLIC_API_URL` hacia la URL pública del Space. Queda fuera de esta
fase (Fase A = solo API).
