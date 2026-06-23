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
