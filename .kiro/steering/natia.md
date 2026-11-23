---
inclusion: always
---

# Contexto: NATIA (app de natación FECNA)

Continúas un proyecto en marcha. Antes de cambiar nada, lee `CLAUDE.md` (carpeta padre del repositorio), `docs/features/pendientes.md` y la nota de la función que toques en `docs/features/`.

## Qué es
App móvil + web con chat en lenguaje natural sobre el ranking de natación de FECNA (Colombia).
- App: Expo / React Native, Expo Router, TypeScript (`mobile/`). Android (APK `co.natia.app`) y web/PWA para iPhone.
- Servidor: FastAPI (`api/`), lógica en `fecna_agent/`.
- Datos: Supabase Postgres en producción y SQLite en local y en pruebas. El adaptador está en `fecna_agent/pg.py`.
- Despliegue:
  - Render: `natia-api` y `natia-app`, se actualizan con cada push a `main` (unos 3 a 5 minutos).
  - Actualizaciones de la app: `cd mobile && npx eas-cli update --channel preview --environment preview --message "<resumen>" --non-interactive`.
  - La web del iPhone solo cambia con el merge a `main`, no con `eas update`.
- Rama de trabajo: `feature/mobile-app`. El repositorio es público.

## Cómo trabajo (respeta esto)
1. Respuestas breves y accionables. Lee solo los archivos necesarios, sin búsquedas amplias.
2. Para cambios pequeños no pidas autorización. Pregunta antes de publicar (merge a `main`, `eas update`), de cambiar configuración sensible y de escribir en producción.
3. Pruebas: una prueba puntual mientras trabajas y el conjunto completo antes de commitear:
   `python3 -m pytest -q --deselect tests/test_pg_live.py`
   App: `cd mobile && npx tsc --noEmit`. No ejecutes `expo lint` (instala ESLint en el proyecto sin pedirlo).
4. Para un bug, escribe primero la prueba que falla, luego el arreglo.
5. Diseño antes de programar: las pantallas nuevas se diseñan en el lienzo de Claude Design (artefacto "FECNA Natación App") y el usuario las aprueba. Después se programan.
6. Commits en español, con `Refs #N` si hay un issue. Termina con push a la rama y pregunta si publicas.
7. Seguridad: no uses secretos reales ni subas datos privados. No pongas datos de menores (nombres, fechas de nacimiento) en commits, issues ni comentarios. Los secretos están en `.env`, que no se versiona.
8. Producción solo se lee, salvo confirmación expresa. Las migraciones van en `PRE_MIGRATIONS_SQL`, `SCHEMA` y `MIGRATIONS_SQL` (`fecna_agent/db.py` y `pg.py`).

## Reglas de diseño del código
- Permisos: cada ruta del servidor exige un permiso (`api/security.py`, `require_permission`) y cada pantalla se oculta por permiso (`mobile/src/app/(tabs)/_layout.tsx`).
  - Un permiso nuevo se agrega en `fecna_agent/permisos.py`.
  - El rol admin lo recibe solo; los demás roles lo activa el admin desde Seguridad.
- Estilo móvil: copia el patrón de las pantallas existentes (`Header`, `Card`, `Chip`, `Button` en `mobile/src/ui.tsx`). Los inputs tienen altura fija de 48.
- Las conexiones a Supabase se abren y cierran cortas: no las dejes abiertas durante llamadas lentas a FECNA.
- FECNA es lento y no se debe sobrecargar. Respeta `DEFAULT_DELAY`.

## Estado actual
Hecho: login obligatorio, roles y permisos editables, chat, ranking, ficha de nadador con todas las marcas, ficha para redes (PNG 9:16), torneos con programas en PDF, menú Configuración (Seguridad, Sincronizar ranking, Cargar programa, Historial de un nadador, Cargar marcas mínimas), pestaña Mínimas, reporte de bugs desde la app hacia GitHub.

Pendiente (detalle en `docs/features/pendientes.md`):
- Que el chat consulte `swimmer_mark` y las marcas mínimas, y un botón "Actualizar historial".
- Roles fase 2 y 3: planes y pagos.
- Mejoras de la ficha para redes (todas las pruebas de un torneo, formato 4:5, escudo del club).
- Que las rutas de lectura validen el estado de la cuenta en cada llamada.
- Que la sincronización también corrija marcas y no solo agregue.
- La prueba `tests/test_pg_live.py` se cuelga: hay que endurecerla.
- Aviso al nadador cuando cumple una marca mínima.
- Derechos de autor, proteger la app (seguridad informática) y crear el «Acerca de».

## Primera tarea
Lee `docs/features/pendientes.md`, resúmeme en 5 líneas qué entendiste del proyecto y pregúntame cuál pendiente atacamos. No cambies código hasta que te lo confirme.
