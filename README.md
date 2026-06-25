# Agente IA - Resultados de natación FECNA

Agente personal para consultar y comparar resultados de natación desde los
reportes públicos de FECNA/Ecoapplet. Ver especificación completa en
`../proyecto_agente_ia_natacion_fecna.md`.

## Estado

- [x] Fase 1: Extracción y almacenamiento local (SQLite)
- [x] Fase 2: Consultas exactas (mejor marca, comparación, ranking, evolución)
- [x] Fase 3: Índice semántico (ChromaDB) + preguntas en lenguaje natural
- [x] Fase 4: Interfaz Streamlit
- [x] Fase 5: Agente IA local (Ollama)
- [x] Fase 6: Programa de campeonato (heat sheet desde PDF)

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Verificación rápida del entorno:

```bash
python3 --version
python -m fecna_agent --help
python -m pytest tests/ -q
```

Si no activas la `.venv`, en algunos sistemas `python` no existe o apunta a un
intérprete sin dependencias (`pandas`, `streamlit`, etc.). En ese caso usa
siempre `source .venv/bin/activate` antes de correr la app o la CLI.

## Uso

```bash
# 1a. Sincronización masiva: todas las pruebas × piscinas × géneros × categorías
python -m fecna_agent catalog   # primero, una vez (y si el sitio cambia)
python -m fecna_agent sync

# 1b. Verificar un campeonato recién terminado: sincroniza desde su fecha de
#     inicio y revisa qué resultados nuevos entraron
python -m fecna_agent sync --inicio 2026-06-01
python -m fecna_agent recent --limit 50

# 1c. Extracción puntual de una sola prueba
python -m fecna_agent fetch --genero M --categoria "12 AÑOS" --prueba 6 --piscina LC

# 2. Consultas sobre la base local
python -m fecna_agent best 1105388915 --prueba 2 --piscina LC
python -m fecna_agent compare 1105388915 1094060609 --prueba 2 --piscina LC
python -m fecna_agent ranking --prueba 2 --piscina LC --limit 10
python -m fecna_agent history 1105388915 --prueba 2

# 3. Índice semántico (una vez, y después de cada fetch para nuevos nadadores)
python -m fecna_agent catalog   # descarga catálogos: pruebas, ligas, piscinas
python -m fecna_agent index     # indexa pruebas (con alias) y nadadores en ChromaDB

# 4. Interfaz web local (Streamlit, multipágina)
streamlit run app.py
# Páginas disponibles: Inicio, Pregunta, Ranking, Comparar, Rankings del nadador,
# Ficha, Programa, Novedades.
# El código común está en `fecna_agent/webui.py`.
# Secciones ocultas: en `disabled_pages/` (muévelas a `pages/` para activarlas).

# 5. Preguntas en lenguaje natural (CLI)
python -m fecna_agent ask "Compara el nadador 1105388915 con el 1094060609 en 50 libre piscina larga"
python -m fecna_agent ask "ranking masculino en 50 libre piscina larga"
python -m fecna_agent ask "evolución de jorge murillo en 50 libre"

# 6. Redacción natural con IA local (requiere Ollama corriendo)
python -m fecna_agent ask --llm "Compara el nadador 1105388915 con el 1094060609 en 50 libre"
python -m fecna_agent ask --llm --model llama3:latest "..."
```

Notas:
- `index --embeddings default` usa el modelo MiniLM de ChromaDB (descarga ~80MB
  la primera vez); por defecto se usa un embedding de tokens offline que
  resuelve bien alias y nombres.
- `ask` solo consulta la base local: extrae primero la prueba que necesites.
- Las categorías están embebidas en el JS de la página y el servidor exige al
  menos una; `catalog` las extrae (por género y másters) y `sync` las envía
  todas juntas en una sola petición por combinación. El select de `torneo`
  sigue sin catálogo: usa rangos de fecha para acotar un campeonato.
- `sync` es idempotente (los resultados repetidos se ignoran por UNIQUE), deja
  bitácora en `sync_log` y estampa los nuevos con el timestamp de la corrida:
  `recent` y la pestaña 🆕 Novedades muestran exactamente qué entró.
- **Error 415 / "being verified"**: ecoapplet.co tiene protección anti-bot.
  Si aparece, `sync` aborta de inmediato (cortacircuito) en vez de insistir.
  Espera unas horas y reintenta. Para reducir la carga sobre el sitio,
  sincroniza incrementalmente con `--inicio` reciente (la base ya conserva
  todo lo histórico; no hace falta repetir el rango completo).
- `--llm` solo redacta: los cálculos vienen de SQL/Python y siempre se anexan
  a la respuesta. Si Ollama no está corriendo, se responde con el texto
  determinístico. Variables: `FECNA_OLLAMA_URL` (defecto `http://localhost:11434`)
  y `FECNA_OLLAMA_MODEL` (defecto: primer modelo instalado).

La base de datos se guarda en `data/fecna.db` (ignorada por git: contiene
datos personales, incluyendo posibles menores — no publicar).

La app Streamlit usa `data/fecna.db` cuando existe. Si no existe, intenta abrir
`data/fecna_public.db` como respaldo de solo lectura/publicable. Para forzar una
base concreta:

```bash
FECNA_DB=data/fecna_public.db streamlit run app.py
```

## Estabilización local

Secuencia recomendada cuando el agente queda inconsistente por cambios de datos,
catálogos o dependencias:

```bash
source .venv/bin/activate
python -m fecna_agent catalog
python -m fecna_agent sync --inicio 2026-06-01
python -m fecna_agent recent --limit 50
python -m fecna_agent index
python -m pytest tests/ -q
streamlit run app.py
```

Notas de diagnóstico:

- Si `catalog` o `sync` abortan con error 415, “being verified” o varios errores
  consecutivos, es bloqueo temporal de Ecoapplet. No borres la base: espera y
  reintenta con `sync --inicio` reciente.
- Si `ask` no identifica pruebas o nadadores por nombre, reconstruye el índice:
  `python -m fecna_agent index`.
- Si la ficha no descarga PNG/PDF, instala el navegador de Playwright:
  `python -m playwright install chromium`. La app seguirá ofreciendo HTML si el
  navegador no está disponible.
- En despliegue público, actualiza datos localmente y publica solo
  `data/fecna_public.db` generado con `python -m fecna_agent anonymize`.

## Pruebas

```bash
python -m pytest tests/ -q
```


## Principio de diseño

```
Requests extrae datos.
SQLite guarda y calcula.
ChromaDB encuentra contexto.   (fase 3)
Python compara.
El LLM explica.                (fase 5)
```

## Programa de campeonato (Fase 6)

La pestaña **📋 Programa** permite cargar el heat sheet (PDF) de un campeonato
y ver, filtrado por club o nadador, qué pruebas debe presentar y a qué hora.

- Soporta dos formatos habituales en Colombia:
  - **HY-TEK MEET MANAGER** (nacionales): `Event 1 Women 10 Year Olds 200 LC Meter IM`
  - **Colombia Acuática / Web Service** (ligas): `67 (M) 11Y - 12Y - 13Y | M`
- Cruza nadadores por nombre normalizado con la base local (los códigos de club
  del PDF son abreviaciones de 4 letras que no coinciden con los nombres completos).
- Los relevos se omiten (no hay ranking individual).
- **Detección de cambios**: si se recarga el mismo PDF sin modificaciones, la
  base no se actualiza (huella SHA-1 del contenido, independiente del orden).

```bash
# Abrir la app y subir el PDF desde la pestaña "Programa"
streamlit run app.py
```

## Acceso (login y registro)

Opcional. La app pide login solo si activas `FECNA_AUTH`:

```bash
FECNA_AUTH=1 FECNA_ADMIN_EMAIL="tu@correo.com" streamlit run app.py
```

- Registro y login con email + contraseña (hash pbkdf2, sin dependencias extra).
- `FECNA_ADMIN_EMAIL` (lista separada por comas) define quién es **admin**; el
  resto son usuarios normales. Solo admin carga/borra programas y sincroniza.
- Sin `FECNA_AUTH`, la app funciona sin login (modo local de siempre).
- Las cuentas viven en `data/fecna.db` (no se publican). **Pendiente (Fase 2):**
  datos por usuario, sesión con cookie y persistencia en la nube — ver
  `docs/superpowers/specs/2026-06-21-login-registro-usuario-design.md`.

## Features por hacer

- **Suscripción de pago para descargar la ficha** — ver
  [docs/features/suscripcion-descarga-ficha.md](docs/features/suscripcion-descarga-ficha.md)
  (login + pasarela colombiana + candado en la pestaña Ficha; decisiones y
  advertencias legales pendientes).
- **Persistir el programa entre despliegues** — ver
  [docs/features/persistencia-programa-despliegue.md](docs/features/persistencia-programa-despliegue.md)
  (el disco de Streamlit Cloud es efímero; opciones: solo local, base externa
  privada o versionar; pendiente por la privacidad de datos de menores).

## Pendientes técnicos

- **`st.components.v1.html` deprecado** (usado en la pestaña Ficha,
  `pages/ficha.py`, para mostrar la infografía en un iframe aislado). Streamlit
  marca su retiro tras 2026-06-01; por ahora sigue funcionando (solo advierte).
  No hay reemplazo directo: `st.html` inyecta el HTML sin aislar su CSS y rompe
  el diseño. Si una actualización de Streamlit lo elimina, migrar a un
  componente con iframe propio o renderizar solo PNG/PDF (Playwright) sin
  previsualización embebida.
- **`packages.txt` no admite comentarios ni espacios**: una línea por paquete
  (Streamlit Cloud pasa cada palabra a `apt-get`).
