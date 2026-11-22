"""Roles y permisos de NATIA: valores de partida.

Rol = quién eres; permiso = qué puedes hacer. Los roles, los permisos y qué permisos tiene cada rol
viven en la base (tablas app_role, app_permission, role_permission) y el admin los edita desde la
app. Aquí solo están los valores con los que se siembra la base la primera vez.

Los permisos «de sistema» están enlazados con el código (cada ruta del servidor exige uno): se les
puede cambiar la etiqueta, pero no borrarlos. Los permisos propios que cree el admin sirven para
funciones futuras (planes, etc.); hoy no abren nada por sí solos.
"""

SYSTEM_PERMISSIONS: dict[str, str] = {
    "ver_ranking": "Ver el ranking",
    "ver_nadador": "Ver la ficha y las marcas de un nadador",
    "ver_torneos": "Ver los campeonatos y sus programas",
    "chat": "Preguntar al chat",
    "comparar": "Comparar nadadores",
    "ficha_redes": "Generar fichas para redes",
    "cargar_programa": "Cargar programas de campeonato",
    "eliminar_programa": "Eliminar programas de campeonato",
    "sincronizar": "Sincronizar el ranking con FECNA",
    "gestionar_usuarios": "Gestionar roles, permisos y usuarios",
}

# id -> (nombre, permisos iniciales). admin siempre tiene todos los permisos.
DEFAULT_ROLES: dict[str, tuple[str, set[str]]] = {
    # Quien se registra solo ve ranking, nadador (sin comparar ni ficha para redes) y torneos.
    "user": ("Usuario", {"ver_ranking", "ver_nadador", "ver_torneos"}),
    "admin": ("Administrador", set(SYSTEM_PERMISSIONS)),
}

ADMIN_ROLE = "admin"  # rol protegido: no se edita ni se borra y conserva todos los permisos
