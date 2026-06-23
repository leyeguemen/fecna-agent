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
2. "Create app" → desde el repo `leyeguemen/fecna-agent`, rama `main`,
   archivo `app.py`.
3. En **Advanced settings → Secrets**, pega:

   ```toml
   FECNA_PUBLIC = "1"
   FECNA_DB = "data/fecna_public.db"
   ```

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

Streamlit redespliega solo al detectar el push.

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
