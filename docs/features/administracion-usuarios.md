Crear modulo de roles y permisos para poder habilitar las opciones de la app

## Cuentas desactivadas (2026-11-23)
- Una cuenta desactivada (`app_user.active = 0`) pierde todo el acceso en máximo 30 s, aunque su token siga vigente. Las rutas usan `require_permission` y las de `/me/*` usan `active_user`.
- **No puede eliminarse a sí misma** desde la app (`DELETE /me` responde 401). Lo pide por correo y el admin la borra. Así, si se desactivó por una sesión robada, quien la robó no puede borrarla. Está en los términos, sección 6.
- Pendiente: botón Activar/Desactivar en Seguridad → Usuarios (diseño en Claude Design por aprobar) y ruta `PUT /admin/users/{id}/active`.
