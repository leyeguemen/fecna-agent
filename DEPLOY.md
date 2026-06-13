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
git add app.py requirements.txt packages.txt .gitignore DEPLOY.md fecna_agent/
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

## Archivos de despliegue ya preparados

- `requirements.txt` — dependencias + `pysqlite3-binary` (ChromaDB lo necesita
  en Linux).
- `packages.txt` — fuente DejaVu para la exportación a PNG.
- `app.py` — modo público (`FECNA_PUBLIC`), base configurable (`FECNA_DB`),
  swap de sqlite y reconstrucción del índice semántico si falta.

## Notas

- Ollama (IA local) no está disponible en la nube; las respuestas siguen siendo
  determinísticas.
- El sistema de archivos de la nube es efímero: la fuente de verdad es el
  `data/fecna_public.db` del repo.

## Alternativa: Hugging Face Spaces

Crea un Space (SDK Streamlit), sube los archivos + `data/fecna_public.db`, y en
*Settings → Variables and secrets* agrega `FECNA_PUBLIC=1` y
`FECNA_DB=data/fecna_public.db`. Mismo `requirements.txt` y `packages.txt`.
