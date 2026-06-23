# Diseño: Login y registro de usuario

Fecha: 2026-06-21

## Objetivo
Agregar autenticación a la app FECNA. Cubre cuatro metas elegidas por el usuario:
proteger el acceso, sentar base para datos por usuario, permitir roles/permisos y
servir de identidad para un cobro futuro (suscripción de ficha, ya documentada
aparte).

## Decisiones
- **Mecanismo:** email + contraseña propios (registro y login), respaldado en la
  base SQLite existente. Se eligió sobre Google/OIDC (requiere montar OAuth y
  secretos externos) y sobre "solo admin" (no permite registro). La lógica de
  auth queda desacoplada del almacenamiento, así que migrar a una base externa
  persistente luego es cambio de infraestructura, no de código de login.
- **Hash:** `hashlib.pbkdf2_hmac` (stdlib, sin dependencias nuevas) con salt por
  usuario. bcrypt queda como mejora opcional (Fase 2).
- **Sesión (Fase 1):** `st.session_state`. Dura lo que la sesión del navegador;
  un refresco duro (F5) obliga a reingresar. La sesión persistente con cookie
  ("recordarme") es Fase 2.
- **Activación:** la app solo exige login si `FECNA_AUTH=1` (env o `st.secrets`).
  En local queda apagado por defecto para no estorbar el desarrollo.

## Alcance por fases

### Fase 1 — la que se construye ahora
1. Tabla `app_user`.
2. Módulo `fecna_agent/auth.py` con la lógica de credenciales.
3. Página `pages/cuenta.py` con login y registro (pestañas).
4. Candado de la app: `webui.require_auth()` llamado en `app.py` antes de
   `st.navigation`. Si `FECNA_AUTH=1` y no hay sesión → muestra login/registro y
   `st.stop()`.
5. Rol `admin`/`user`. El primer usuario registrado, o el email en
   `FECNA_ADMIN_EMAIL`, queda como `admin`.
6. Botón "Cerrar sesión" en la barra lateral.
7. Las acciones sensibles (cargar/borrar programa, sincronizar) pasan a requerir
   rol **admin**. En Fase 1 los **programas siguen siendo compartidos**: cualquier
   usuario autenticado los consulta; solo admin los carga o borra. (El scoping
   real por usuario es Fase 2.)

### Fase 2 — documentada, pendiente
- **Datos por usuario:** columna `user_id` en `competition` y/o
  `competition_watch` para aislar programas/alertas/seguidos por dueño.
- **Sesión persistente (cookie "recordarme"):** requiere un componente de cookies
  (p. ej. `extra-streamlit-components`) o migrar a `st.login` nativo.
- **Persistencia en la nube:** las cuentas (como los programas) se pierden en cada
  deploy por el disco efímero de Streamlit Cloud. Ver
  `docs/features/persistencia-programa-despliegue.md`: la solución (base externa
  privada tipo Turso/libSQL) es compartida con ese pendiente.
- **Google / OIDC** (`st.login`) como alternativa o complemento de login.
- **bcrypt** en vez de pbkdf2.
- **Enganche de cobro:** atar la suscripción de descarga de ficha a la identidad.

## Modelo de datos
Nueva tabla (se crea sola en bases existentes vía `CREATE TABLE IF NOT EXISTS`):

```sql
CREATE TABLE IF NOT EXISTS app_user (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  salt          TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'user',  -- 'admin' | 'user'
  active        INTEGER NOT NULL DEFAULT 1,
  created_at    TIMESTAMP
);
```

El email se normaliza a minúsculas/trim antes de guardar y comparar.

## Componentes

### `fecna_agent/auth.py`
Funciones puras, sin Streamlit, testeables de forma aislada:
- `hash_password(password, salt=None) -> (hash_hex, salt_hex)`:
  `pbkdf2_hmac('sha256', password, salt, 200_000)`, salt de 16 bytes.
- `verify_password(password, hash_hex, salt_hex) -> bool`: comparación en tiempo
  constante con `hmac.compare_digest`.
- `normalize_email(email) -> str`.
- `valid_email(email) -> bool` y `valid_password(password) -> str|None` (regla
  mínima: ≥ 8 caracteres; devuelve mensaje de error o None).

### `fecna_agent/db.py` (funciones nuevas)
- `create_user(conn, email, password, role='user') -> dict`: valida unicidad,
  hashea, inserta. Devuelve error claro si el email ya existe.
- `get_user_by_email(conn, email) -> Row|None`.
- `authenticate(conn, email, password) -> Row|None`: busca, verifica hash,
  exige `active=1`.
- `count_users(conn) -> int`: para decidir si el registro es el primer usuario
  (→ admin).
- `set_role(conn, user_id, role)` (utilitario para administración futura).

### `fecna_agent/webui.py`
- `current_user() -> Row|None`: lee `st.session_state['auth_user']`.
- `is_admin() -> bool`.
- `require_auth()`: si `FECNA_AUTH` está activo y no hay usuario en sesión,
  renderiza login/registro y `st.stop()`. Si está apagado, no hace nada.
- `logout()`: limpia la sesión.
- `AUTH = _auth_mode()` análogo a `PUBLIC`.

### `pages/cuenta.py`
Dos pestañas: **Iniciar sesión** y **Registrarse**.
- Login: email + password → `db.authenticate` → si ok, guarda el usuario en
  `session_state` y `st.rerun()`; si no, error.
- Registro: email + password + confirmación → valida → `db.create_user`
  (el primer usuario o `FECNA_ADMIN_EMAIL` ⇒ admin) → inicia sesión.

### `app.py`
Tras `webui.bootstrap()` y antes de construir/`run` la navegación:
`webui.require_auth()`. Así ninguna página se renderiza sin sesión cuando el
candado está activo.

### Gating por rol
Reemplazar/complementar los checks actuales `not webui.PUBLIC` de acciones
sensibles por `webui.is_admin()` cuando el candado está activo. Donde hoy se usa
`PUBLIC` para anonimizar datos mostrados, se conserva (es otra preocupación).

## Flujo
1. Usuario abre la app. Si `FECNA_AUTH=1` y no hay sesión → `pages/cuenta.py`.
2. Se registra (primer usuario ⇒ admin) o inicia sesión.
3. La sesión queda en `session_state`; la barra lateral muestra el email y
   "Cerrar sesión".
4. Las páginas funcionan normal; las acciones de admin solo aparecen/ejecutan
   para `role='admin'`.

## Manejo de errores
- Email duplicado en registro → mensaje claro, no excepción cruda.
- Credenciales inválidas → mensaje genérico ("email o contraseña incorrectos")
  para no filtrar qué existe.
- Contraseña corta / email inválido → validación antes de tocar la base.
- Usuario inactivo (`active=0`) → no autentica.

## Pruebas (TDD)
Unidad (sin Streamlit), en `tests/test_auth.py`:
- `hash_password` produce hashes distintos por salt; `verify_password` valida
  correcto/incorrecto.
- `create_user` + `authenticate` (caso ok, contraseña errada, email inexistente,
  inactivo).
- email duplicado rechazado.
- primer usuario obtiene rol admin; los siguientes, user.
- `normalize_email`/`valid_email`/`valid_password` casos borde.

## Privacidad y secretos (CLAUDE.md)
- Sin secretos reales en el repo. `FECNA_ADMIN_EMAIL` y `FECNA_AUTH` por
  env/`st.secrets`.
- No se publican contraseñas ni hashes (la tabla `app_user` vive en `fecna.db`,
  ignorada por git; `export_anonymized` NO la copia).
- En el despliegue público actual, mientras no haya persistencia externa, las
  cuentas no sobreviven a un redeploy: por eso Fase 1 está pensada para uso local
  y la persistencia en la nube es Fase 2.

## Fuera de alcance (Fase 1)
Recuperación de contraseña por email, verificación de email, OAuth, cookies de
sesión persistente, datos por usuario, y cualquier integración de pago.
