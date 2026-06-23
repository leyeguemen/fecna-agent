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
