# Login y registro de usuario — Plan de implementación (Fase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar autenticación email+contraseña (registro y login), con roles admin/user, que protege la app cuando se activa.

**Architecture:** Lógica pura de credenciales en `fecna_agent/auth.py` (sin Streamlit), persistencia de usuarios en SQLite vía `fecna_agent/db.py`, y el candado + UI de sesión en `fecna_agent/webui.py` (se invoca desde `app.py` antes de `st.navigation`). Las acciones sensibles pasan a requerir rol admin.

**Tech Stack:** Python stdlib (`hashlib.pbkdf2_hmac`, `hmac`, `re`, `os`), SQLite, Streamlit ≥1.37, pytest.

## Global Constraints

- **Sin dependencias nuevas:** hashing con `hashlib.pbkdf2_hmac` (stdlib). No bcrypt/passlib en Fase 1.
- **Sin secretos reales en el repo.** `FECNA_AUTH` y `FECNA_ADMIN_EMAIL` se leen de env o `st.secrets`, igual que `FECNA_PUBLIC`.
- **Candado apagado por defecto:** si `FECNA_AUTH` no está activo, la app funciona sin login (modo local actual).
- **Admin solo por `FECNA_ADMIN_EMAIL`** (lista separada por comas, emails normalizados). No existe "primer usuario = admin".
- **Contraseña válida:** ≥ 8 caracteres, con al menos una letra y un dígito.
- **Privacidad:** la tabla `app_user` vive en `data/fecna.db` (ignorada por git); `export_anonymized` NO la copia (no se toca esa función).
- **UI en español.**
- **TDD + commits frecuentes.** Tests con `pytest tests/ -q` (hoy 84 pasan).

---

### Task 1: Módulo `fecna_agent/auth.py` (lógica pura)

**Files:**
- Create: `fecna_agent/auth.py`
- Test: `tests/test_auth.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `hash_password(password: str, salt: str | bytes | None = None) -> tuple[str, str]` → `(hash_hex, salt_hex)`
  - `verify_password(password: str, hash_hex: str, salt_hex: str) -> bool`
  - `normalize_email(email: str) -> str`
  - `valid_email(email: str) -> bool`
  - `valid_password(password: str) -> str | None` (mensaje de error o None)
  - `parse_admin_emails(raw: str | None) -> list[str]`
  - `role_for(email: str, admin_emails: list[str]) -> str` → `"admin"` | `"user"`

- [ ] **Step 1: Write the failing test**

Crear `tests/test_auth.py`:

```python
"""Pruebas de la lógica pura de autenticación (sin Streamlit)."""

from fecna_agent import auth


def test_hash_password_distinto_por_salt_y_verifica():
    h1, s1 = auth.hash_password("Secreta123")
    h2, s2 = auth.hash_password("Secreta123")
    assert s1 != s2 and h1 != h2          # salt aleatorio por hash
    assert auth.verify_password("Secreta123", h1, s1)
    assert not auth.verify_password("otra", h1, s1)


def test_hash_password_reproducible_con_mismo_salt():
    h1, s1 = auth.hash_password("Secreta123")
    h2, s2 = auth.hash_password("Secreta123", s1)
    assert h2 == h1 and s2 == s1


def test_normalize_email():
    assert auth.normalize_email("  Juan@Mail.COM ") == "juan@mail.com"


def test_valid_email():
    assert auth.valid_email("a@b.co")
    assert not auth.valid_email("sin-arroba")
    assert not auth.valid_email("a@b")


def test_valid_password():
    assert auth.valid_password("Secreta123") is None
    assert auth.valid_password("corta1") is not None        # < 8
    assert auth.valid_password("sololetras") is not None     # sin dígito
    assert auth.valid_password("12345678") is not None       # sin letra


def test_parse_admin_emails_y_role_for():
    admins = auth.parse_admin_emails(" Jefe@Mail.com , otro@x.co ")
    assert admins == ["jefe@mail.com", "otro@x.co"]
    assert auth.role_for("JEFE@mail.com", admins) == "admin"
    assert auth.role_for("nadie@x.co", admins) == "user"
    assert auth.role_for("a@b.co", auth.parse_admin_emails(None)) == "user"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_auth.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'fecna_agent.auth'`.

- [ ] **Step 3: Write minimal implementation**

Crear `fecna_agent/auth.py`:

```python
"""Lógica pura de autenticación: hashing, validación y roles.

Sin dependencias de Streamlit ni de la base, para poder probarse aislada. El
hash usa pbkdf2_hmac (stdlib): sin dependencias nuevas.
"""

import hashlib
import hmac
import os
import re

_ITERATIONS = 200_000
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_password(password: str, salt: str | bytes | None = None) -> tuple[str, str]:
    """Devuelve (hash_hex, salt_hex). Si no se pasa salt, genera uno aleatorio."""
    if salt is None:
        salt = os.urandom(16)
    elif isinstance(salt, str):
        salt = bytes.fromhex(salt)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return dk.hex(), salt.hex()


def verify_password(password: str, hash_hex: str, salt_hex: str) -> bool:
    """Compara en tiempo constante la contraseña contra el hash guardado."""
    calc, _ = hash_password(password, salt_hex)
    return hmac.compare_digest(calc, hash_hex)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(normalize_email(email)))


def valid_password(password: str) -> str | None:
    """None si es válida; si no, un mensaje de error en español."""
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if not re.search(r"[A-Za-z]", password):
        return "La contraseña debe incluir al menos una letra."
    if not re.search(r"\d", password):
        return "La contraseña debe incluir al menos un dígito."
    return None


def parse_admin_emails(raw: str | None) -> list[str]:
    """'a@x.co, B@y.co' -> ['a@x.co', 'b@y.co']. None/'' -> []."""
    if not raw:
        return []
    return [normalize_email(e) for e in raw.split(",") if e.strip()]


def role_for(email: str, admin_emails: list[str]) -> str:
    return "admin" if normalize_email(email) in set(admin_emails) else "user"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_auth.py -q`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add fecna_agent/auth.py tests/test_auth.py
git commit -m "feat(auth): lógica pura de hashing, validación y roles"
```

---

### Task 2: Tabla `app_user` y funciones de usuario en `db.py`

**Files:**
- Modify: `fecna_agent/db.py` (añadir tabla al `SCHEMA`; añadir funciones cerca de las demás de dominio)
- Test: `tests/test_auth_db.py`

**Interfaces:**
- Consumes: `fecna_agent.auth` (Task 1), `db.connect`.
- Produces:
  - `create_user(conn, email: str, password: str, role: str = "user") -> dict`
  - `get_user_by_email(conn, email: str) -> sqlite3.Row | None`
  - `authenticate(conn, email: str, password: str) -> sqlite3.Row | None`
  - `set_role(conn, user_id: int, role: str) -> None`

- [ ] **Step 1: Write the failing test**

Crear `tests/test_auth_db.py`:

```python
"""Pruebas de usuarios sobre la base (en memoria)."""

import pytest

from fecna_agent import db


def _conn():
    return db.connect(":memory:")


def test_create_y_authenticate():
    conn = _conn()
    u = db.create_user(conn, "Coach@Mail.com", "Secreta123")
    assert u["email"] == "coach@mail.com"      # normalizado
    assert u["role"] == "user"
    assert db.authenticate(conn, "coach@mail.com", "Secreta123") is not None
    assert db.authenticate(conn, "coach@mail.com", "mala") is None
    assert db.authenticate(conn, "noexiste@x.co", "Secreta123") is None


def test_email_duplicado_rechazado():
    conn = _conn()
    db.create_user(conn, "a@b.co", "Secreta123")
    with pytest.raises(ValueError):
        db.create_user(conn, "A@b.co", "Secreta123")


def test_password_invalida_rechazada():
    conn = _conn()
    with pytest.raises(ValueError):
        db.create_user(conn, "a@b.co", "corta1")


def test_usuario_inactivo_no_autentica():
    conn = _conn()
    u = db.create_user(conn, "a@b.co", "Secreta123")
    conn.execute("UPDATE app_user SET active = 0 WHERE id = ?", (u["id"],))
    conn.commit()
    assert db.authenticate(conn, "a@b.co", "Secreta123") is None


def test_create_user_con_rol_admin():
    conn = _conn()
    u = db.create_user(conn, "jefe@x.co", "Secreta123", role="admin")
    assert u["role"] == "admin"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_auth_db.py -q`
Expected: FAIL con `AttributeError: module 'fecna_agent.db' has no attribute 'create_user'`.

- [ ] **Step 3: Write minimal implementation**

En `fecna_agent/db.py`, añadir la tabla al final del `SCHEMA` (justo antes de la triple comilla de cierre, tras `competition_watch`):

```sql

CREATE TABLE IF NOT EXISTS app_user (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  salt          TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'user',
  active        INTEGER NOT NULL DEFAULT 1,
  created_at    TIMESTAMP
);
```

Y añadir las funciones (por ejemplo tras `watched_schedule`):

```python
def create_user(
    conn: sqlite3.Connection, email: str, password: str, role: str = "user"
) -> dict:
    """Crea un usuario (valida email/contraseña/unicidad). Devuelve el registro.

    Lanza ValueError con mensaje en español si algo no cumple."""
    from datetime import datetime

    from . import auth

    email = auth.normalize_email(email)
    if not auth.valid_email(email):
        raise ValueError("Email inválido.")
    err = auth.valid_password(password)
    if err:
        raise ValueError(err)
    if get_user_by_email(conn, email) is not None:
        raise ValueError("Ese email ya está registrado.")
    hash_hex, salt_hex = auth.hash_password(password)
    conn.execute(
        """INSERT INTO app_user (email, password_hash, salt, role, active, created_at)
           VALUES (?, ?, ?, ?, 1, ?)""",
        (email, hash_hex, salt_hex, role,
         datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    return dict(get_user_by_email(conn, email))


def get_user_by_email(conn: sqlite3.Connection, email: str):
    from . import auth
    return conn.execute(
        "SELECT * FROM app_user WHERE email = ?", (auth.normalize_email(email),)
    ).fetchone()


def authenticate(conn: sqlite3.Connection, email: str, password: str):
    """Devuelve el Row del usuario si las credenciales son válidas y está activo."""
    from . import auth
    row = get_user_by_email(conn, email)
    if not row or not row["active"]:
        return None
    if auth.verify_password(password, row["password_hash"], row["salt"]):
        return row
    return None


def set_role(conn: sqlite3.Connection, user_id: int, role: str) -> None:
    conn.execute("UPDATE app_user SET role = ? WHERE id = ?", (role, user_id))
    conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_auth_db.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Run full suite to confirm no regressions**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS (todos; el `app_user` no afecta otras tablas).

- [ ] **Step 6: Commit**

```bash
git add fecna_agent/db.py tests/test_auth_db.py
git commit -m "feat(auth): tabla app_user y create_user/authenticate/get_user/set_role"
```

---

### Task 3: Modo auth, helpers y candado en `webui.py`

**Files:**
- Modify: `fecna_agent/webui.py`
- Test: `tests/test_auth_webui.py`

**Interfaces:**
- Consumes: `fecna_agent.auth` (Task 1), `db.authenticate`/`db.create_user` (Task 2), `get_conn`.
- Produces:
  - `AUTH: bool` (módulo)
  - `admin_emails() -> list[str]`
  - `current_user() -> dict | None`
  - `is_admin() -> bool`
  - `require_auth() -> None`  (renderiza login/registro y `st.stop()` si aplica)
  - `render_login_register(conn) -> None`
  - `logout() -> None`

**Nota de diseño:** la UI de login/registro va en `webui` (no en una página de
`pages/`) porque el candado corre en `app.py` *antes* de `st.navigation`, y las
páginas solo se renderizan dentro de la navegación. (Desviación consciente del
spec, que mencionaba `pages/cuenta.py`.)

- [ ] **Step 1: Write the failing test**

Crear `tests/test_auth_webui.py` (prueba la lógica testeable sin render):

```python
"""Pruebas de helpers de auth en webui que no dependen del render de Streamlit."""

from fecna_agent import webui


def test_is_admin_sin_auth_es_true(monkeypatch):
    # Con el candado apagado, la app es de acceso total (modo local).
    monkeypatch.setattr(webui, "AUTH", False)
    assert webui.is_admin() is True


def test_is_admin_con_auth_sin_sesion_es_false(monkeypatch):
    monkeypatch.setattr(webui, "AUTH", True)
    monkeypatch.setattr(webui, "current_user", lambda: None)
    assert webui.is_admin() is False


def test_is_admin_con_auth_y_rol(monkeypatch):
    monkeypatch.setattr(webui, "AUTH", True)
    monkeypatch.setattr(webui, "current_user", lambda: {"role": "admin"})
    assert webui.is_admin() is True
    monkeypatch.setattr(webui, "current_user", lambda: {"role": "user"})
    assert webui.is_admin() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_auth_webui.py -q`
Expected: FAIL (`AttributeError: ... 'is_admin'` o `'AUTH'`).

- [ ] **Step 3: Write minimal implementation**

En `fecna_agent/webui.py`, junto a `_public_mode`/`PUBLIC` (cerca de la línea 60), añadir:

```python
def _auth_mode() -> bool:
    if os.environ.get("FECNA_AUTH"):
        return True
    try:
        return bool(st.secrets.get("FECNA_AUTH", False))
    except Exception:
        return False


AUTH = _auth_mode()


def admin_emails() -> list[str]:
    raw = os.environ.get("FECNA_ADMIN_EMAIL")
    if not raw:
        try:
            raw = st.secrets.get("FECNA_ADMIN_EMAIL", "")
        except Exception:
            raw = ""
    from . import auth
    return auth.parse_admin_emails(raw)


def current_user():
    """Usuario en sesión (dict) o None."""
    return st.session_state.get("auth_user")


def is_admin() -> bool:
    """Sin candado, acceso total (modo local). Con candado, solo rol admin."""
    if not AUTH:
        return True
    user = current_user()
    return bool(user and user.get("role") == "admin")


def logout() -> None:
    st.session_state.pop("auth_user", None)
    st.rerun()


def render_login_register(conn) -> None:
    """Formularios de inicio de sesión y registro (pestañas)."""
    from . import auth, db as database

    st.title("🔐 Acceso")
    tab_login, tab_reg = st.tabs(["Iniciar sesión", "Registrarse"])

    with tab_login:
        with st.form("login"):
            email = st.text_input("Email")
            pwd = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar", type="primary"):
                user = database.authenticate(conn, email, pwd)
                if user:
                    st.session_state["auth_user"] = dict(user)
                    st.rerun()
                else:
                    st.error("Email o contraseña incorrectos.")

    with tab_reg:
        with st.form("registro"):
            email = st.text_input("Email", key="reg_email")
            pwd = st.text_input("Contraseña", type="password", key="reg_pwd")
            pwd2 = st.text_input("Repite la contraseña", type="password", key="reg_pwd2")
            if st.form_submit_button("Crear cuenta", type="primary"):
                if pwd != pwd2:
                    st.error("Las contraseñas no coinciden.")
                else:
                    try:
                        role = auth.role_for(email, admin_emails())
                        user = database.create_user(conn, email, pwd, role=role)
                        st.session_state["auth_user"] = user
                        st.success("Cuenta creada.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))


def require_auth() -> None:
    """Si el candado está activo y no hay sesión, muestra el acceso y detiene."""
    if not AUTH or current_user():
        return
    render_login_register(get_conn())
    st.stop()
```

En `bootstrap()`, mostrar sesión/logout y atar los controles de admin al rol.
Reemplazar el bloque final:

```python
    if not PUBLIC:
        with st.sidebar:
            admin_controls(conn)
```

por:

```python
    with st.sidebar:
        user = current_user()
        if AUTH and user:
            st.caption(f"👤 {user['email']}")
            if st.button("Cerrar sesión"):
                logout()
        if not PUBLIC and is_admin():
            admin_controls(conn)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_auth_webui.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add fecna_agent/webui.py tests/test_auth_webui.py
git commit -m "feat(auth): modo FECNA_AUTH, candado require_auth y sesión en webui"
```

---

### Task 4: Candado en `app.py` y gating por rol en Programa

**Files:**
- Modify: `app.py` (llamar `webui.require_auth()` antes de `st.navigation`)
- Modify: `pages/programa.py` (subida y borrado de programa solo para admin)

**Interfaces:**
- Consumes: `webui.require_auth`, `webui.is_admin` (Task 3).
- Produces: nada nuevo (cambios de integración).

- [ ] **Step 1: Modificar `app.py`**

Tras `webui.bootstrap()` y antes de construir `PAGINAS`/`st.navigation`, añadir:

```python
# Barra lateral común (estadísticas + controles). Antes de st.navigation.
webui.bootstrap()

# Candado de acceso: si FECNA_AUTH está activo y no hay sesión, muestra el
# formulario de acceso y detiene el render del resto de la app.
webui.require_auth()
```

- [ ] **Step 2: Gating de la subida de programa en `pages/programa.py`**

Envolver el expander de carga (hoy siempre visible) para que solo aparezca a
admins. Cambiar:

```python
with st.expander("➕ Cargar un nuevo programa (PDF)", expanded=False):
```

por:

```python
if webui.is_admin():
  with st.expander("➕ Cargar un nuevo programa (PDF)", expanded=False):
```

(Indentar el cuerpo del expander un nivel; el resto de la página queda igual.)

Y el botón de borrar ya usa `not webui.PUBLIC`; cambiarlo a admin:

```python
if webui.is_admin() and col_c.button("🗑️", help="Eliminar este programa"):
```

- [ ] **Step 3: Verificar import**

Run: `.venv/bin/python -c "import ast; ast.parse(open('app.py').read()); ast.parse(open('pages/programa.py').read()); print('OK')"`
Expected: `OK`.

- [ ] **Step 4: Smoke test manual del candado**

Run: `FECNA_AUTH=1 FECNA_ADMIN_EMAIL=jefe@mail.com .venv/bin/streamlit run app.py`
Verificar:
1. Sin sesión aparece "🔐 Acceso" (login/registro) y ninguna página.
2. Registrarse con `jefe@mail.com` → entra como admin (ve controles y la carga de programa).
3. Registrarse con otro email → entra como user (no ve carga ni borrado de programa).
4. "Cerrar sesión" vuelve al acceso.
5. Sin la variable (`.venv/bin/streamlit run app.py`) la app funciona sin login (modo local).

- [ ] **Step 5: Run full suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: PASS (todos).

- [ ] **Step 6: Commit**

```bash
git add app.py pages/programa.py
git commit -m "feat(auth): candado de acceso en app y carga de programa solo admin"
```

---

### Task 5: Documentación

**Files:**
- Modify: `README.md` (sección breve de autenticación + variables)
- Modify: `DEPLOY.md` (nota: cuentas no persisten en la nube hasta Fase 2)

**Interfaces:** ninguna.

- [ ] **Step 1: README — añadir sección**

En `README.md`, bajo el estado o tras "Programa de campeonato", añadir:

```markdown
## Acceso (login y registro)

Opcional. La app pide login solo si activas `FECNA_AUTH`:

```bash
FECNA_AUTH=1 FECNA_ADMIN_EMAIL="tu@correo.com" streamlit run app.py
```

- Registro y login con email + contraseña (hash pbkdf2, sin dependencias extra).
- `FECNA_ADMIN_EMAIL` (lista separada por comas) define quién es **admin**; el
  resto son usuarios normales. Solo admin carga/borra programas y sincroniza.
- Sin `FECNA_AUTH`, la app funciona sin login (modo local de siempre).
- Las cuentas viven en `data/fecna.db` (no se publican). **Pendiente (Fase 2):**
  datos por usuario, sesión con cookie y persistencia en la nube — ver
  `docs/superpowers/specs/2026-06-21-login-registro-usuario-design.md`.
```

- [ ] **Step 2: DEPLOY — añadir nota**

En `DEPLOY.md`, en "Notas", añadir un bullet:

```markdown
- Si activas `FECNA_AUTH`, las cuentas se guardan en SQLite y **no sobreviven a
  un redeploy** (disco efímero). Persistirlas requiere una base externa — ver
  `docs/features/persistencia-programa-despliegue.md` (mismo pendiente).
```

- [ ] **Step 3: Commit**

```bash
git add README.md DEPLOY.md
git commit -m "docs(auth): cómo activar login, roles y nota de persistencia en la nube"
```

---

## Self-Review

**Spec coverage:**
- Tabla `app_user` → Task 2 ✅
- `auth.py` (hash/verify/validación/roles) → Task 1 ✅
- Funciones db (create/get/authenticate/set_role) → Task 2 ✅
- `require_auth`/`current_user`/`is_admin`/`logout`/UI → Task 3 ✅
- Candado en `app.py` + gating por rol → Task 4 ✅
- Admin solo por `FECNA_ADMIN_EMAIL` → Task 1 (`role_for`) + Task 3 (`admin_emails`) ✅
- Contraseña letra+dígito → Task 1 (`valid_password`) ✅
- `FECNA_AUTH` apagado por defecto → Task 3 (`_auth_mode`) ✅
- Pruebas → Tasks 1, 2, 3 ✅
- Privacidad (app_user no exportada) → Global Constraints; `export_anonymized` no se toca ✅
- Docs/pendientes Fase 2 → Task 5 ✅
- **Desviación documentada:** UI de acceso en `webui` en vez de `pages/cuenta.py` (justificada por el orden de render). No afecta el alcance.

**Placeholder scan:** sin TBD/TODO; todo el código está completo.

**Type consistency:** `hash_password`/`verify_password`, `role_for(email, admin_emails)`, `create_user(...) -> dict`, `authenticate(...) -> Row|None`, `is_admin() -> bool`, `current_user() -> dict|None` se usan consistentes entre tareas.
