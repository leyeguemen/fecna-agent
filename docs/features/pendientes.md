# Planes pendientes (2026-11-21)

Todo lo que quedó para trabajar luego, por orden de utilidad. Cada punto indica dónde está el detalle.

## Funciones nuevas
1. ~~Marcas mínimas del campeonato nacional~~ — **hecho** (tabla `minimum_mark` con el Reglamento FECNA 2026, pestaña *Mínimas* y corrección por el admin en Configuración; ver `fecna_agent/minimas.py`). Pendiente de esta línea: que el chat consulte las mínimas, aviso al nadador cuando cumple una marca y la ventana de fechas en que cuentan. Detalle en `docs/features/marcas-minimas.md`.
2. **Roles y permisos, fases 2 y 3** — planes con límites (chat, fichas, nadadores seguidos) y pasarela de pago. La fase 1 (CRUD de roles, permisos y usuarios en la pestaña *Seguridad*) ya está hecha. Detalle y cuidados en `docs/features/roles-permisos.md`. Antes hay que decidir **dónde se cobra** (tiendas Google/Apple 15–30 % vs web) y revisar el modelo con un asesor legal.
3. ~~Historial completo de marcas de FECNA~~ — **hecho** para nadadores seguidos/vinculados (tabla `swimmer_mark`, no altera rankings; ver `fecna_agent/historial.py`). Pendiente de esta línea: que el chat consulte `swimmer_mark` (hoy solo ve `ranking_public`), y un botón «Actualizar historial».
4. **Ficha para redes, mejoras:**
   - ficha por campeonato con **todas las pruebas** (formato más alto);
   - versión **4:5** para el feed de Instagram (hoy es 9:16);
   - **escudo real del club** (hoy es el nombre dentro de un círculo): subir el logo por club;
   - **puesto dentro del torneo** (hoy «Nac.» solo sale si la marca es su mejor de esa prueba): habría que traerlo de FECNA.

5. ~~Skill `/bugs`~~ — **hecha** (`.claude/skills/bugs/`): lista los issues, toma uno, lo reproduce, lo corrige con pruebas y lo deja «por probar». Detalle en `docs/features/reportes-bugs.md`.
6. ~~Landing page~~ — **hecha**: página estática en `/bienvenida` del sitio web (`mobile/public/bienvenida/index.html`), enlazada desde el Login web. Pendiente: enlace de descarga del APK cuando haya uno estable.
7. ~~Torneos: agrupar por nadador~~ — **hecho**: el programa de un torneo se ve por nadador (tarjetas que se abren con sus pruebas): «Tus nadadores» (vinculado, seguidos y vigilados) arriba y el resto debajo, con un buscador por nombre o club que filtra ambos. Se sumó la pantalla de **Inicio** (`/me/home`) como entrada tras iniciar sesión y Configuración pasó al Perfil.
8. ~~Recuperar contraseña~~ — **hecho**: «¿Olvidaste tu contraseña?» en el Login (`/recuperar`). La API (`/auth/forgot`, `/auth/reset`) envía un código de 6 dígitos por correo con Brevo; vence en 15 min, 5 intentos, reenvío cada 60 s, y al cambiarla cierra las demás sesiones. Requiere `BREVO_API_KEY` y `MAIL_FROM` en `natia-api`.

## Pulido y deuda técnica
9. ~~Las rutas validan solo el token~~ — **hecho**: ranking, nadadores, torneos y chat ya usaban `require_permission`; las de la propia cuenta (`/me/*`) ahora usan `active_user`. Una cuenta desactivada o borrada pierde el acceso en máximo 30 s (caché de `current_access`), no al vencer el token.
10. **La sincronización solo agrega**: no refleja correcciones ni borrados de FECNA. Si importa, una sincronización completa periódica con comparación.
11. **Día irrecuperable** `2025-11-06` (50 y 100 libre F LC): el servidor de FECNA falla con 500 en ese día; nada que hacer salvo que lo corrijan.
12. **Test en vivo contra Supabase** (`tests/test_pg_live.py`) se cuelga si el pooler está lleno; conviene un timeout.
13. **iPhone nativo** necesitaría cuenta Apple Developer (99 USD/año); hoy es la web instalada (PWA).

## Legal, seguridad y presentación
14. **Derechos de autor** — definir y declarar la autoría y la licencia de la app y del código, y el uso de los datos de FECNA.
15. **Proteger la app (seguridad informática)** — auditoría del 2026-11-23. Hecho:
   - La base local con datos personales salió del repositorio y de su historial.
   - El SQL libre del chat se valida con lista blanca (`sqlglot`) y corre en solo lectura con tiempo máximo.
   - Los límites de intentos usan la IP real (`CF-Connecting-IP`, en `api/routers/auth.py`).
   - Cambiar la contraseña cierra las demás sesiones (`password_changed_at`).
   - `/docs` está apagado en Render.
   - La web envía cabeceras de seguridad.
   - El aviso de los reportes pide no incluir datos de menores.

   Falta:
   - Un rol de Postgres restringido para el chat (requiere escribir en producción).
   - Una CSP para la web, probada en el navegador.
   - Limitar CORS al dominio de `natia-app`.
   - Actualizar Expo cuando corrija `minimatch` (`npm audit`, solo herramientas de compilación).
   - Pedir a GitHub Support la purga de los commits viejos.
16. **Crear el «Acerca de»** — pantalla con la información de la app.

## Operativos (los haces tú)
- Borrar los servicios viejos de Render `fecna-api` y `fecna-app` cuando ya no uses el APK anterior.
- **Rotar la contraseña de la base de datos** en Supabase (una vez se coló en un commit local, sin llegar a subirse) y actualizar `DATABASE_URL` en `natia-api`, en los secretos de GitHub Actions y en tu `.env`.
- Revisión legal de los **términos y condiciones** (cita la Ley 1581 de 2012; ya tiene el correo de contacto).
- Probar con cuentas de prueba los roles y la restricción del usuario nuevo.
- Activar el tablero de bugs (3 pasos en `docs/features/reportes-bugs.md`).
