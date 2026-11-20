"""Tests de /competitions: lectura pública, seguidos por usuario y carga/borrado admin.

El PDF de carga se sustituye por monkeypatch de `programa.parse_pdf` (devuelve
`parse_text(HYTEK)`, el mismo texto HY-TEK de tests/test_programa.py): evita la
fragilidad de generar un PDF con fpdf2 y luego extraerlo con pdfplumber, y sigue
ejerciendo de punta a punta el endpoint (multipart, auth, mapeo, cruce y guardado).
"""

import os

import pytest
from fastapi.testclient import TestClient

from fecna_agent import db, programa

HYTEK = """\
Federacion Colombiana de Natacion HY-TEK's MEET MANAGER 8.0
2026 CAMPEONATO NACIONAL INFANTIL INTERCLUBES - 5/06/2026 to 7/06/2026
Event 14 Men 11 Year Olds 100 LC Meter Freestyle
Lane Name Age Team Seed Time
Heat 2 of 2 Finals Starts at 09:59 AM
0 Aaron Daniel Camacho 11 CFEN 1:15.69
4 Angel David Caballero Pinzon 11 AQUS 1:10.51
Event 1 Women 10 Year Olds 200 LC Meter IM
Lane Name Age Team Seed Time
Heat 1 of 2 Finals Starts at 08:30 AM
3 Luciana Sanchez Gutierrez 10 CDDQ 3:36.22
Event 25 Mixed 10 Year Olds 200 LC Meter Medley Relay
Lane Team Relay Seed Time
Heat 1 of 1 Finals Starts at 10:32 AM
4 DOM X12 A 5:13.62
"""


@pytest.fixture
def client(tmp_path, monkeypatch):
    read_path = tmp_path / "read.db"
    conn = db.connect(read_path)
    db.save_catalogs(conn, {"prueba": [("100L", "100m Libre")]})
    db.insert_results(conn, [{
        "source": "test", "ranking_position": None,
        "swimmer_id": "999", "swimmer_name": "Aaron Daniel Camacho",
        "first_name": None, "last_name": None, "gender": "M",
        "birth_date": None, "birth_year_month": None,
        "event_id": "100L", "event_name": "100m Libre", "pool_type": "LC",
        "time_raw": "00:01:15.69", "time_ms": 75690, "points": None,
        "result_date": "2026-01-01", "league": None, "club": "CFEN",
        "fetched_at": None,
    }])
    conn.close()

    monkeypatch.setenv("FECNA_DB", str(read_path))
    monkeypatch.setenv("FECNA_APP_DB", str(tmp_path / "app.db"))
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("FECNA_ADMIN_EMAIL", raising=False)

    from api import main
    return TestClient(main.app)


def _register(client, email, monkeypatch=None, admin=False, password="Secreta123"):
    if admin:
        monkeypatch.setenv("FECNA_ADMIN_EMAIL", email)
    resp = client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201
    return resp.json()["token"]


def _mock_parse_pdf(monkeypatch):
    monkeypatch.setattr(
        "api.routers.competitions.programa.parse_pdf",
        lambda source: programa.parse_text(HYTEK),
    )


def _upload(client, headers):
    return client.post(
        "/competitions",
        headers=headers,
        files={"file": ("programa.pdf", b"contenido-simulado", "application/pdf")},
    )


# --- Carga (admin) ---------------------------------------------------------------
def test_upload_sin_token_401(client):
    resp = _upload(client, headers={})
    assert resp.status_code == 401


def test_upload_usuario_normal_403(client, monkeypatch):
    _mock_parse_pdf(monkeypatch)
    token = _register(client, "user@x.co")
    resp = _upload(client, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_upload_admin_crea_y_reupload_no_cambia(client, monkeypatch):
    _mock_parse_pdf(monkeypatch)
    token = _register(client, "admin@x.co", monkeypatch=monkeypatch, admin=True)
    headers = {"Authorization": f"Bearer {token}"}

    resp = _upload(client, headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "created"
    assert body["entradas"] == 3  # el relevo se omite
    assert body["cruzados"] == 1  # Aaron Daniel Camacho está en la base de lectura
    comp_id = body["competition_id"]

    resp2 = _upload(client, headers)
    assert resp2.status_code == 201
    assert resp2.json()["status"] == "unchanged"
    assert resp2.json()["competition_id"] == comp_id


def test_upload_content_type_no_pdf_400(client, monkeypatch):
    token = _register(client, "admin@x.co", monkeypatch=monkeypatch, admin=True)
    resp = client.post(
        "/competitions",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("programa.txt", b"no soy un pdf", "text/plain")},
    )
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]


def test_upload_pdf_demasiado_grande_400(client, monkeypatch):
    token = _register(client, "admin@x.co", monkeypatch=monkeypatch, admin=True)
    grande = b"x" * (10 * 1024 * 1024 + 1)
    resp = client.post(
        "/competitions",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("programa.pdf", grande, "application/pdf")},
    )
    assert resp.status_code == 400
    assert "10 MB" in resp.json()["detail"]


def test_upload_sin_inscripciones_400(client, monkeypatch):
    monkeypatch.setattr(
        "api.routers.competitions.programa.parse_pdf",
        lambda source: ({"name": "Vacío", "pool_type": "LC"}, []),
    )
    token = _register(client, "admin@x.co", monkeypatch=monkeypatch, admin=True)
    headers = {"Authorization": f"Bearer {token}"}
    resp = _upload(client, headers)
    assert resp.status_code == 400
    assert "inscripciones" in resp.json()["detail"]


# --- Lectura pública ---------------------------------------------------------------
def _uploaded_comp(client, monkeypatch):
    _mock_parse_pdf(monkeypatch)
    token = _register(client, "admin@x.co", monkeypatch=monkeypatch, admin=True)
    headers = {"Authorization": f"Bearer {token}"}
    comp_id = _upload(client, headers).json()["competition_id"]
    return comp_id, headers


def test_list_competitions(client, monkeypatch):
    comp_id, _ = _uploaded_comp(client, monkeypatch)
    resp = client.get("/competitions")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert items[0]["id"] == comp_id
    assert items[0]["entradas"] == 3


def test_schedule_filtra_por_swimmer(client, monkeypatch):
    comp_id, _ = _uploaded_comp(client, monkeypatch)
    resp = client.get(f"/competitions/{comp_id}/schedule",
                       params={"swimmer": "Aaron Daniel Camacho"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["swimmer_name"] == "Aaron Daniel Camacho"
    assert items[0]["club_code"] == "CFEN"
    assert items[0]["seed"] == "01:15.69"
    assert items[0]["swimmer_id"] == "999"


def test_clubs_and_swimmers(client, monkeypatch):
    comp_id, _ = _uploaded_comp(client, monkeypatch)
    clubs = client.get(f"/competitions/{comp_id}/clubs").json()["items"]
    assert set(clubs) == {"CFEN", "AQUS", "CDDQ"}
    swimmers = client.get(f"/competitions/{comp_id}/swimmers").json()["items"]
    names = {s["swimmer_name"] for s in swimmers}
    assert "Aaron Daniel Camacho" in names


# --- Seguidos por usuario ------------------------------------------------------------
def test_watch_aislado_entre_usuarios_y_legacy_no_visible(client, monkeypatch):
    comp_id, _ = _uploaded_comp(client, monkeypatch)

    # Watch "global"/legacy (Streamlit histórico, user_id por defecto = 0).
    conn = db.connect(os.environ["FECNA_APP_DB"])
    db.set_watched(conn, comp_id, ["Angel David Caballero Pinzon"])
    conn.close()

    token_a = _register(client, "a@x.co")
    token_b = _register(client, "b@x.co")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    put_a = client.put(f"/competitions/{comp_id}/watch",
                        headers=headers_a, json={"names": ["Aaron Daniel Camacho"]})
    assert put_a.status_code == 200
    assert put_a.json()["names"] == ["Aaron Daniel Camacho"]

    put_b = client.put(f"/competitions/{comp_id}/watch",
                        headers=headers_b, json={"names": ["Luciana Sanchez Gutierrez"]})
    assert put_b.json()["names"] == ["Luciana Sanchez Gutierrez"]

    get_a = client.get(f"/competitions/{comp_id}/watch", headers=headers_a)
    get_b = client.get(f"/competitions/{comp_id}/watch", headers=headers_b)
    assert get_a.json()["names"] == ["Aaron Daniel Camacho"]
    assert get_b.json()["names"] == ["Luciana Sanchez Gutierrez"]
    # Ninguno ve el seguimiento legado (user_id=0), ni el del otro usuario.
    assert "Angel David Caballero Pinzon" not in get_a.json()["names"]
    assert "Angel David Caballero Pinzon" not in get_b.json()["names"]


def test_watch_sin_token_401(client, monkeypatch):
    comp_id, _ = _uploaded_comp(client, monkeypatch)
    assert client.get(f"/competitions/{comp_id}/watch").status_code == 401
    assert client.put(f"/competitions/{comp_id}/watch", json={"names": []}).status_code == 401


def test_alerts_devuelve_solo_lo_del_usuario(client, monkeypatch):
    comp_id, _ = _uploaded_comp(client, monkeypatch)
    token_a = _register(client, "a@x.co")
    token_b = _register(client, "b@x.co")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    client.put(f"/competitions/{comp_id}/watch", headers=headers_a,
               json={"names": ["Aaron Daniel Camacho"]})

    alerts_a = client.get(f"/competitions/{comp_id}/alerts", headers=headers_a)
    alerts_b = client.get(f"/competitions/{comp_id}/alerts", headers=headers_b)
    assert alerts_a.status_code == 200
    assert [i["swimmer_name"] for i in alerts_a.json()["items"]] == ["Aaron Daniel Camacho"]
    assert alerts_b.json()["items"] == []


# --- Borrado (admin) ---------------------------------------------------------------
def test_delete_requiere_admin_y_hace_cascada(client, monkeypatch):
    comp_id, admin_headers = _uploaded_comp(client, monkeypatch)
    token_user = _register(client, "user@x.co")

    resp_no_token = client.delete(f"/competitions/{comp_id}")
    assert resp_no_token.status_code == 401

    resp_user = client.delete(f"/competitions/{comp_id}",
                               headers={"Authorization": f"Bearer {token_user}"})
    assert resp_user.status_code == 403

    resp_admin = client.delete(f"/competitions/{comp_id}", headers=admin_headers)
    assert resp_admin.status_code == 204

    # Cascada: ya no aparece en el listado ni tiene cronograma.
    assert client.get("/competitions").json()["items"] == []
    assert client.get(f"/competitions/{comp_id}/schedule").json()["items"] == []
