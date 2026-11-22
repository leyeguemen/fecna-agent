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
- Catálogo en `fecna_agent/permisos.py` (roles `user`/`admin`, 7 permisos) y rol en `app_user.role`.
- Servidor: `security.require_permission(perm)`. Para acciones de administrador lee el **rol vigente de la base** (caché 30 s), así quitar un rol o borrar una cuenta surte efecto en segundos y no a los 7 días del token. Sincronizar, cargar/eliminar programa y gestionar usuarios lo usan; `chat`, `comparar` y `ficha_redes` usan el rol del token.
- API: `/auth/login`, `/auth/register` y `/auth/me` devuelven `permissions`; `GET /admin/roles`, `GET /admin/users`, `PUT /admin/users/{id}/role` (no permite cambiar el propio rol ni quitar al último admin).
- App: `useAuth().can(permiso)`; la pestaña Admin y sus tarjetas, y el botón de eliminar programa, aparecen según permisos; tarjeta «Usuarios y roles» en Admin.
- Límite conocido: las rutas de lectura (ranking, nadadores) siguen validando solo el token; una cuenta desactivada conserva ese acceso hasta que venza (7 días).
