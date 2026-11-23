Crear modulo de roles y permisos para poder habilitar las opciones de la app

## Cuentas desactivadas (2026-11-23)
- Una cuenta desactivada (`app_user.active = 0`) pierde todo el acceso en máximo 30 s, aunque su token siga vigente. Las rutas usan `require_permission` y las de `/me/*` usan `active_user`.
- **No puede eliminarse a sí misma** desde la app (`DELETE /me` responde 401). Lo pide por correo y el admin la borra. Así, si se desactivó por una sesión robada, quien la robó no puede borrarla. Está en los términos, sección 6.
- El admin activa y desactiva cuentas en Seguridad → Usuarios (`PUT /admin/users/{id}/active`). No puede desactivarse a sí mismo ni al último administrador activo.
- Al iniciar sesión, una cuenta desactivada con la **clave correcta** recibe 403 y el mensaje «Tu cuenta está desactivada. Escribe a …». Con la clave equivocada recibe el error genérico, así no se revela qué correos tienen cuenta (`db.check_login`). El correo está en `CONTACT_EMAIL` (`api/routers/auth.py`) y debe coincidir con el de los términos.
