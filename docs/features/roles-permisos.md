# Módulo de roles y permisos (y suscripción a futuro)

Idea: poder habilitar o deshabilitar opciones de la app por rol y, cuando se piense cobrar, gestionarlo desde ahí.

**Estado:** fase 1 implementada (2026-11-21). Fases 2 y 3 pendientes de decidir el modelo de negocio.

## Modelo
- **Rol = quién eres:** usuario, admin; más adelante entrenador o club.
- **Permiso = qué puedes hacer:** `chat`, `ficha_redes`, `comparar`, `cargar_programa`, `eliminar_programa`, `sincronizar`…
- **Plan = qué pagaste:** activa un conjunto de permisos y límites (preguntas al chat por día, fichas por mes, nadadores seguidos).

Hoy solo existe `user`/`admin` fijo y un límite diario de chat igual para todos (`FECNA_ASK_DAILY_LIMIT`).

## Fases
1. **Barata, sin decisiones de negocio:** permisos definidos en código, tabla que asigna roles/planes a usuarios, `/me` devuelve `permissions`, la app muestra u oculta opciones según ellos, pantalla de Admin para cambiar el rol de un usuario. Reemplaza las comprobaciones `role == 'admin'`.
2. **Al decidir cobrar:** planes con límites (chat, fichas, seguidos).
3. **Después:** pasarela de pago que solo activa/desactiva el plan.

## Cuidados
- El servidor valida cada permiso; la app solo oculta botones.
- No construir un editor de permisos libres todavía (complejidad sin uso).
- Pagos dentro de la app Android/iPhone suelen exigir el cobro de Google/Apple (15–30 %); por la web (Wompi, Stripe) no aplica. Decidir antes de diseñar el cobro.
- Se cobraría el análisis (chat, fichas, alertas), no los datos públicos de FECNA; revisar términos con un asesor legal y la relación con FECNA.
- Los permisos nunca abren más datos de menores que los que hoy ve cualquier usuario con sesión.

## Fase 1: lo que quedó
- **Roles y permisos en la base** (tablas `app_role`, `app_permission`, `role_permission`), sembrados con los valores de `fecna_agent/permisos.py` (roles `user`/`admin`, 7 permisos de sistema). El admin los edita desde la app.
- **Pestaña «Roles»** (solo con el permiso `gestionar_usuarios`) con tres secciones: *Usuarios* (cambiar el rol de cada uno), *Roles* (crear, editar nombre y permisos, eliminar) y *Permisos* (crear, editar etiqueta, eliminar).
- Reglas: el rol **Administrador** no se edita ni se elimina y siempre recibe todos los permisos (también los nuevos); los roles de sistema no se eliminan; un rol con usuarios asignados no se elimina; los permisos **de sistema** (los usa el código) no se eliminan, solo se les cambia la etiqueta; los permisos **propios** sirven para funciones futuras y hoy no abren nada por sí solos; no se puede cambiar el propio rol ni quitar al último admin.
- Servidor: `security.require_permission(perm)` lee rol y permisos **vigentes de la base** (caché de 30 s; se limpia al editar). Cambiar un rol, editar sus permisos o borrar una cuenta surte efecto en segundos, no a los 7 días del token. Protegen sincronizar, cargar/eliminar programa, gestionar usuarios, chat, comparar y ficha para redes.
- API: `/auth/login|register|me` devuelven `permissions`; `GET/POST /admin/roles`, `PUT/DELETE /admin/roles/{id}`, `POST /admin/permissions`, `PUT/DELETE /admin/permissions/{key}`, `GET /admin/users`, `PUT /admin/users/{id}/role`.
- App: `useAuth().can(permiso)` muestra u oculta pestañas, tarjetas y botones.
- Límite conocido: las rutas de lectura (ranking, nadadores) solo validan el token; una cuenta desactivada conserva ese acceso hasta que venza (7 días).
