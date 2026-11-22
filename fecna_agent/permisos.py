"""Roles y permisos de NATIA.

Rol = quién eres; permiso = qué puedes hacer. El catálogo vive aquí (en código) y el rol de cada
usuario en app_user.role. Más adelante un «plan» (suscripción) podrá sumar permisos y límites
sin tocar las pantallas: solo se pregunta «¿tiene este permiso?».
"""

ROLES: dict[str, str] = {
    "user": "Usuario",
    "admin": "Administrador",
}

PERMISSIONS: dict[str, str] = {
    "chat": "Preguntar al chat",
    "comparar": "Comparar nadadores",
    "ficha_redes": "Generar fichas para redes",
    "cargar_programa": "Cargar programas de campeonato",
    "eliminar_programa": "Eliminar programas de campeonato",
    "sincronizar": "Sincronizar el ranking con FECNA",
    "gestionar_usuarios": "Gestionar los roles de los usuarios",
}

_BASE = {"chat", "comparar", "ficha_redes"}

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "user": frozenset(_BASE),
    "admin": frozenset(PERMISSIONS),
}


def permissions_for(role: str | None) -> list[str]:
    """Permisos del rol, ordenados. Un rol desconocido no recibe ninguno."""
    return sorted(ROLE_PERMISSIONS.get(role or "", frozenset()))


def has(role: str | None, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role or "", frozenset())


def catalog() -> dict:
    """Roles con sus permisos, para mostrarlos en Admin."""
    return {
        "roles": [
            {"id": rid, "name": name,
             "permissions": [{"key": p, "label": PERMISSIONS[p]} for p in permissions_for(rid)]}
            for rid, name in ROLES.items()
        ],
        "permissions": [{"key": k, "label": v} for k, v in PERMISSIONS.items()],
    }
