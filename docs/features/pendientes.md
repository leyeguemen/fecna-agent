# Planes pendientes (2026-11-21)

Todo lo que quedó para trabajar luego, por orden de utilidad. Cada punto indica dónde está el detalle.

## Funciones nuevas
1. **Marcas mínimas del campeonato nacional** — el admin carga el documento oficial; el chat y el perfil comparan con las marcas del nadador. Plan y dudas abiertas en `docs/features/marcas-minimas.md`. Falta un **ejemplo real del documento** (PDF/Excel) para empezar.
2. **Roles y permisos, fases 2 y 3** — planes con límites (chat, fichas, nadadores seguidos) y pasarela de pago. La fase 1 (CRUD de roles, permisos y usuarios en la pestaña *Seguridad*) ya está hecha. Detalle y cuidados en `docs/features/roles-permisos.md`. Antes hay que decidir **dónde se cobra** (tiendas Google/Apple 15–30 % vs web) y revisar el modelo con un asesor legal.
3. ~~Historial completo de marcas de FECNA~~ — **hecho** para nadadores seguidos/vinculados (tabla `swimmer_mark`, no altera rankings; ver `fecna_agent/historial.py`). Pendiente de esta línea: que el chat consulte `swimmer_mark` (hoy solo ve `ranking_public`), y un botón «Actualizar historial».
4. **Ficha para redes, mejoras:**
   - ficha por campeonato con **todas las pruebas** (formato más alto);
   - versión **4:5** para el feed de Instagram (hoy es 9:16);
   - **escudo real del club** (hoy es el nombre dentro de un círculo): subir el logo por club;
   - **puesto dentro del torneo** (hoy «Nac.» solo sale si la marca es su mejor de esa prueba): habría que traerlo de FECNA.

5. ~~Skill `/bugs`~~ — **hecha** (`.claude/skills/bugs/`): lista los issues, toma uno, lo reproduce, lo corrige con pruebas y lo deja «por probar». Detalle en `docs/features/reportes-bugs.md`.

## Pulido y deuda técnica
6. **Las rutas de lectura** (ranking, nadadores) validan solo el token: una cuenta desactivada conserva ese acceso hasta que venza (7 días). Pasarlas a la consulta vigente (ya existe `require_permission`).
7. **La sincronización solo agrega**: no refleja correcciones ni borrados de FECNA. Si importa, una sincronización completa periódica con comparación.
8. **Día irrecuperable** `2025-11-06` (50 y 100 libre F LC): el servidor de FECNA falla con 500 en ese día; nada que hacer salvo que lo corrijan.
9. **Test en vivo contra Supabase** (`tests/test_pg_live.py`) se cuelga si el pooler está lleno; conviene un timeout.
10. **iPhone nativo** necesitaría cuenta Apple Developer (99 USD/año); hoy es la web instalada (PWA).

## Legal, seguridad y presentación
11. **Derechos de autor** — definir y declarar la autoría y la licencia de la app y del código, y el uso de los datos de FECNA.
12. **Proteger la app (seguridad informática)** — revisar y endurecer la seguridad de la app, el servidor y la base de datos.
13. **Crear el «Acerca de»** — pantalla con la información de la app.

## Operativos (los haces tú)
- Borrar los servicios viejos de Render `fecna-api` y `fecna-app` cuando ya no uses el APK anterior.
- **Rotar la contraseña de la base de datos** en Supabase (una vez se coló en un commit local, sin llegar a subirse) y actualizar `DATABASE_URL` en `natia-api`, en los secretos de GitHub Actions y en tu `.env`.
- Revisión legal de los **términos y condiciones** (cita la Ley 1581 de 2012; ya tiene el correo de contacto).
- Probar con cuentas de prueba los roles y la restricción del usuario nuevo.
- Activar el tablero de bugs (3 pasos en `docs/features/reportes-bugs.md`).
