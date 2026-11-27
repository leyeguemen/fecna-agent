# Despliegue

## App móvil + API (gratis)

Arquitectura: app Expo → API FastAPI (Render) → Supabase Postgres. La sincronización del
ranking corre en GitHub Actions (`.github/workflows/sync.yml`) y escribe en Supabase.

### 1. API en Render
1. Render → **New → Blueprint** → elige este repo (rama `main`). Lee `render.yaml`.
2. Completa las variables que pide (nunca van en el repo):
   - `DATABASE_URL`: cadena del **Session pooler** de Supabase.
   - `ANTHROPIC_API_KEY`, `FECNA_JWT_SECRET` (`openssl rand -hex 32`), `FECNA_ADMIN_EMAIL`.
   - `GITHUB_TOKEN`: fine-grained, solo este repo, permiso *Actions: read/write*.
3. Cuando termine, prueba `https://<tu-servicio>.onrender.com/health`.

El plan gratis "duerme" tras 15 min sin tráfico: la primera petición tarda ~50 s (la app lo avisa).

### 2. App móvil
- Desarrollo: `mobile/.env` → `EXPO_PUBLIC_API_URL=https://<tu-servicio>.onrender.com`, luego `npx expo start`.
- Distribución: `npx eas-cli build -p android --profile preview` (APK instalable, gratis en cola
  estándar) o publicar como actualización OTA con `eas update`.

### Actualizaciones por aire (EAS Update)
Los cambios de código de la app (pantallas, textos, lógica) llegan al APK ya instalado **sin recompilar**:
```bash
cd mobile
npx eas-cli update --channel preview --message "qué cambió"
```
El APK las descarga al abrirse (la primera apertura baja la actualización, la siguiente la aplica).
- **Solo hay que recompilar el APK** cuando cambia algo nativo: instalar o quitar un paquete con módulo
  nativo (`expo-file-system`, `expo-sharing`, etc.), cambiar `app.json` (íconos, permisos, nombre) o subir de
  versión de Expo. Al hacerlo, sube también `version` en `mobile/app.json`: las actualizaciones solo se
  entregan a APK con la misma versión (`runtimeVersion` por `appVersion`).
- Variables `EXPO_PUBLIC_*`: se incrustan al publicar; `mobile/.env` debe tener `EXPO_PUBLIC_API_URL`.
- La versión web (iPhone) no usa esto: se despliega sola en Render al hacer merge a `main`.

### 3. Sincronización
GitHub → Settings → Secrets → Actions: `DATABASE_URL` (mismo valor). La ejecución semanal corre
sola (lunes 04:00 hora Colombia) y el botón de Admin de la app la dispara a demanda.

### Variables de entorno de la API
| Variable | Para qué |
|---|---|
| `DATABASE_URL` | Postgres de Supabase (Session pooler) |
| `ANTHROPIC_API_KEY` | Chat con Claude; sin ella se usa el agente determinístico |
| `FECNA_CLAUDE_MODEL` | Modelo (por defecto `claude-haiku-5-5`) |
| `FECNA_JWT_SECRET` | Firma de sesiones (obligatoria en producción) |
| `FECNA_ADMIN_EMAIL` | Correos con rol admin (separados por coma) |
| `FECNA_ASK_DAILY_LIMIT` | Preguntas por usuario al día (50) |
| `GITHUB_TOKEN` / `GITHUB_REPO` / `GITHUB_REF` | Disparar la sincronización desde Admin |

### Recuperar la versión anterior (Streamlit + Next.js)
La etiqueta `pre-mobile-cleanup` conserva el estado previo a la limpieza:
`git checkout pre-mobile-cleanup`.

## Flujo de ramas
- `feature/*` → PR a **`develop`** (integración; no despliega nada).
- Para desplegar el grupo de cambios: un solo PR **`develop` → `main`**.
  Al hacer merge a `main` se despliega Render y se publica la app (EAS Update).
- Crear features desde `develop`: `git checkout develop && git pull && git checkout -b feature/x`.
- PR de un feature: `gh pr create --base develop`.
- PR de despliegue: `gh pr create --base main --head develop --title "Release AAAA-MM-DD"`.
  Usar **merge commit** (no squash) para que `develop` y `main` no diverjan.
