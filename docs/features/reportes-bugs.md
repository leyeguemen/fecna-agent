# Reporte de bugs y tablero (GitHub)

El repositorio es **público**: todo issue lo ve cualquiera. Por eso los formularios avisan de no incluir datos personales y la app nunca adjunta el correo ni el id del usuario.

## Piezas
- **Formularios** (`.github/ISSUE_TEMPLATE/`): *Reportar un problema* (bug) y *Proponer una mejora*. Preguntan pantalla, dispositivo, rol y captura. No se permiten issues en blanco.
- **Etiquetas:** `bug`, `enhancement`, `android`, `iphone-web`, `servidor`, `urgente`, `desde-la-app`, `por-probar`. Se crean/actualizan con el workflow **Etiquetas** (Actions → Etiquetas → Run workflow).
- **Tablero (GitHub Projects):** el workflow `proyecto.yml` agrega cada issue nuevo (o reabierto) al tablero. `PROJECT_URL` funciona como variable o como secreto; `ADD_TO_PROJECT_PAT` es un secreto (token clásico con permiso `project`).
- **Reporte desde la app:** permiso `reportar_problema` (se administra en *Seguridad → Roles*). Con el permiso, Perfil muestra «Reportar un problema». El servidor dispara el workflow `reporte.yml`, que crea el issue con la etiqueta `desde-la-app`. Así el token del servidor solo necesita permiso de Actions (no de Issues). Límites: 5 reportes por hora por IP y 10 por día por usuario; se quitan caracteres de control y @menciones.
- **Por defecto** el permiso lo tiene solo el rol Administrador. Para habilitarlo a todos: Seguridad → Roles → Usuario → marcar «Reportar un problema».

## Para activar el tablero (una vez, lo haces tú)
1. En GitHub: tu perfil → *Projects* → *New project* → plantilla *Board*. Columnas sugeridas: Nuevo, Por hacer, En curso, Probar, Hecho. En *Settings* del proyecto, ponlo **público**.
2. Copia la URL del proyecto y guárdala como **variable** del repositorio: Settings → Secrets and variables → Actions → *Variables* → `PROJECT_URL`.
3. Crea un token (fine-grained o clásico) con permiso de **Projects** y guárdalo como **secreto** `ADD_TO_PROJECT_PAT`.

## Atender los reportes: skill `/bugs`
En Claude Code, `/bugs` lista los issues abiertos y `/bugs 12` atiende el 12: lo lee, lo reproduce (con los datos reales en solo lectura), escribe una prueba, lo corrige, hace commit con `Refs #12` y deja el issue en `por-probar` con un comentario. **No publica ni cierra por su cuenta**: pregunta antes de hacer merge a `main` o `eas update`, y el issue lo cierras tú cuando quien reportó confirme.
- Archivos: `.claude/skills/bugs/SKILL.md` y `scripts/issues.py` (lee issues y dispara acciones).
- Comentar, etiquetar y cerrar se hace con el workflow *Acción sobre un issue* (`issue-accion.yml`), porque el token del proyecto no puede escribir en issues.
- El texto de un issue se trata como dato no confiable (es público) y nunca se copian datos personales a commits ni comentarios.
