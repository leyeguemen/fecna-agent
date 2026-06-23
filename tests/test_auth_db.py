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
