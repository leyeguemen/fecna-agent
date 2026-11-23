"""Marcas mínimas de los campeonatos nacionales (Reglamento FECNA 2026, art. 13): datos de partida y cálculo.

Las tablas del reglamento vienen como imagen, no como texto: se transcribieron una vez (abajo) y el admin las
puede corregir desde la app. Son marcas de piscina larga (50 m). La categoría sale de la edad: año del
campeonato menos año de nacimiento."""

import re

POOL = "LC"
YEAR = 2026

# (event_id de FECNA, etiqueta corta) en el orden del reglamento.
EVENTS = [("2", "50 L"), ("3", "100 L"), ("4", "200 L"), ("5", "400 L"), ("6", "800 L"), ("7", "1500 L"),
          ("9", "50 E"), ("10", "100 E"), ("11", "200 E"), ("13", "50 P"), ("14", "100 P"), ("15", "200 P"),
          ("17", "50 M"), ("18", "100 M"), ("19", "200 M"), ("21", "200 CI"), ("22", "400 CI")]
EVENT_LABEL = dict(EVENTS)

TOURNAMENTS = {"infantiles": "Infantiles", "interligas": "Interligas", "interclubes": "Interclubes"}
_CAT_LABELS = {"10": "10 años", "11": "11 años", "12": "12 años", "13": "13 años", "14": "14 años", "15": "15 años",
               "juvb": "Juvenil B · 16–17", "junior": "Junior · 18–20", "mayores": "Mayores"}
CATEGORIES = {"infantiles": ["10", "11", "12", "13"], "interligas": ["14", "15", "juvb", "junior", "mayores"],
              "interclubes": ["14", "15", "juvb", "junior", "mayores"]}
GENDERS = ("M", "F")


def category_label(category: str) -> str:
    return _CAT_LABELS.get(category, category)


def category_for(tournament: str, age: int | None) -> str | None:
    """Categoría del nadador en ese campeonato, o None si por edad no aplica."""
    if age is None:
        return None
    if tournament == "infantiles":
        return str(age) if 10 <= age <= 13 else None
    if age < 14:
        return None
    return "14" if age == 14 else "15" if age == 15 else "juvb" if age <= 17 else "junior" if age <= 20 else "mayores"


_TIME = re.compile(r"^\s*(?:(\d{1,2}):)?(?:(\d{1,2}):)?(\d{1,2})[,.](\d{1,2})\s*$")


def parse_time(text: str) -> int:
    """'1:58,85' o '00:24,71' → milisegundos."""
    m = _TIME.match(text or "")
    if not m:
        raise ValueError(f"Tiempo no válido: {text!r} (usa mm:ss,cc)")
    a, b, sec, cs = m.groups()
    minutes = int(a) * 60 + int(b) if b is not None else int(a) if a is not None else 0
    if int(sec) > 59:
        raise ValueError(f"Tiempo no válido: {text!r}")
    return (minutes * 60 + int(sec)) * 1000 + int(cs.ljust(2, "0")) * 10


def format_time(ms: int) -> str:
    minutes, rest = divmod(ms, 60_000)
    return f"{minutes:02d}:{rest // 1000:02d},{rest % 1000 // 10:02d}"


def format_diff(ms: int) -> str:
    """Diferencia en segundos: 340 → '0,34 s'; 73 s → '1:13,00' no aplica: siempre en s con coma."""
    return f"{abs(ms) / 1000:.2f}".replace(".", ",") + " s"


def evaluate(marks: dict[str, int], best: dict[str, int]) -> dict:
    """marks: event_id → mínima (ms). best: event_id → mejor marca del nadador en piscina larga (ms)."""
    rows, met = [], 0
    for event_id, label in EVENTS:
        if event_id not in marks:
            continue
        minima, mine = marks[event_id], best.get(event_id)
        if mine is None:
            status, diff = "sin_marca", None
        elif mine <= minima:
            status, diff = "cumple", minima - mine
            met += 1
        else:
            status, diff = "falta", mine - minima
        rows.append({"event_id": event_id, "event": label, "minima_ms": minima, "minima": format_time(minima),
                     "best_ms": mine, "best": format_time(mine) if mine is not None else None,
                     "status": status, "diff_ms": diff, "diff": format_diff(diff) if diff is not None else None})
    return {"rows": rows, "met": met, "total": len(rows)}


# --- Datos del reglamento 2026 (transcritos de las tablas del PDF) ---------------------------------
def _t(s: str | None):
    return None if s in (None, "-") else parse_time(s)


# event_id → (masculino, femenino) en el orden VISUAL de cada tabla.
_INFANTILES = {  # M: 10,11,12,13 · F: 13,12,11,10
    "2": ("38,03 34,71 31,57 29,51", "31,69 32,87 34,73 38,76"),
    "3": ("1:24,79 1:17,40 1:09,72 1:05,79", "1:09,23 1:11,58 1:16,22 1:27,16"),
    "4": ("3:08,71 2:49,45 2:32,19 2:23,66", "2:30,55 2:36,94 2:50,33 3:10,51"),
    "5": ("6:33,15 5:57,41 5:27,88 5:05,12", "5:23,40 5:35,95 6:03,91 6:40,30"),
    "6": ("- 12:46,57 11:36,88 10:40,42", "11:15,76 11:44,59 12:55,05 -"),
    "7": ("- - - 20:53,49", "21:55,19 - - -"),
    "9": ("48,51 42,11 - -", "- - 42,30 47,00"),
    "10": ("- 1:31,55 1:26,26 1:19,28", "1:21,39 1:26,19 1:31,78 -"),
    "11": ("- - 3:05,84 2:48,88", "2:56,75 3:04,29 - -"),
    "13": ("53,87 48,95 - -", "- - 48,12 53,95"),
    "14": ("- 1:48,11 1:36,89 1:28,42", "1:32,92 1:36,83 1:46,47 -"),
    "15": ("- - 3:29,93 3:11,68", "3:24,85 3:30,14 - -"),
    "17": ("45,08 40,14 - -", "- - 39,85 48,46"),
    "18": ("- 1:37,95 1:23,83 1:16,09", "1:21,84 1:27,33 1:40,54 -"),
    "19": ("- - 3:24,49 3:08,57", "3:17,57 3:34,78 - -"),
    "21": ("3:40,99 3:11,61 2:58,35 2:44,89", "2:54,51 3:01,59 3:13,92 3:38,35"),
    "22": ("- - 6:54,10 6:16,88", "6:13,41 6:42,50 - -"),
}
# M: mayores, junior, juvb, 15, 14 · F (visual): 14, 15, juvb, junior, mayores
_INTERLIGAS = {
    "2": ("24,71 25,21 25,55 26,52 27,23", "30,47 30,47 29,56 29,17 28,79"),
    "3": ("54,59 54,73 55,60 58,38 59,13", "1:06,24 1:06,24 1:04,47 1:03,12 1:01,77"),
    "4": ("1:58,85 2:01,28 2:03,71 2:09,55 2:11,28", "2:28,25 2:27,36 2:22,08 2:19,10 2:16,12"),
    "5": ("4:23,21 4:26,13 4:28,39 4:38,87 4:48,11", "5:11,79 5:16,25 5:04,21 5:01,36 4:58,51"),
    "6": ("9:25,88 9:28,30 9:30,71 9:41,01 10:02,46", "10:54,82 10:37,38 10:14,92 10:10,85 10:06,77"),
    "7": ("18:10,19 18:17,51 18:24,83 18:47,07 19:26,75", "20:59,87 20:10,21 19:27,56 19:19,83 19:12,10"),
    "9": ("29,44 29,45 29,78 31,61 33,04", "36,37 35,96 34,60 34,07 33,55"),
    "10": ("1:05,10 1:05,11 1:05,29 1:09,25 1:11,94", "1:20,14 1:19,05 1:15,98 1:15,98 1:14,38"),
    "11": ("2:23,82 2:23,82 2:23,82 2:34,56 2:38,81", "2:51,95 2:52,22 2:45,53 2:45,20 2:44,88"),
    "13": ("31,70 32,21 32,72 34,30 35,94", "41,02 41,01 39,34 38,83 38,32"),
    "14": ("1:11,11 1:12,78 1:13,95 1:19,15 1:21,42", "1:31,71 1:30,80 1:27,07 1:26,20 1:25,33"),
    "15": ("2:39,14 2:41,68 2:44,23 2:52,18 3:01,44", "3:21,46 3:19,19 3:10,19 3:09,39 3:08,59"),
    "17": ("26,39 26,76 27,13 28,23 29,29", "33,25 33,05 31,69 31,34 30,99"),
    "18": ("58,95 1:00,00 1:00,31 1:03,85 1:07,00", "1:19,10 1:17,44 1:12,94 1:11,73 1:10,51"),
    "19": ("2:22,42 2:22,42 2:22,42 2:36,87 2:44,50", "3:08,18 3:03,92 2:57,86 2:56,98 2:56,10"),
    "21": ("2:21,02 2:22,07 2:23,11 2:29,21 2:32,49", "2:50,37 2:53,36 2:42,72 2:42,23 2:41,75"),
    "22": ("5:05,19 5:07,24 5:09,29 5:32,62 5:47,67", "6:04,57 5:50,20 5:37,86 5:35,62 5:33,38"),
}
_INTERCLUBES = {
    "2": ("25,02 25,29 25,55 26,52 27,23", "30,79 30,79 29,94 29,63 29,00"),
    "3": ("54,73 54,73 56,19 58,38 59,76", "1:07,68 1:07,68 1:05,32 1:04,28 1:03,24"),
    "4": ("2:01,11 2:03,20 2:04,24 2:09,55 2:13,27", "2:29,57 2:29,57 2:23,92 2:21,91 2:19,91"),
    "5": ("4:30,14 4:30,14 4:28,39 4:38,87 4:48,25", "5:18,79 5:18,79 5:10,59 5:07,80 5:05,01"),
    "6": ("9:33,30 9:33,30 9:33,30 9:41,01 10:02,46", "11:17,47 11:17,47 11:02,82 10:47,33 10:32,04"),
    "7": ("18:32,45 18:33,39 18:33,39 18:47,07 19:26,75", "22:25,75 21:46,14 20:59,87 20:35,04 20:10,21"),
    "9": ("29,45 29,45 29,78 31,61 33,04", "37,42 36,79 35,73 35,40 35,07"),
    "10": ("1:05,11 1:05,11 1:05,29 1:09,25 1:11,94", "1:21,40 1:20,85 1:17,43 1:17,09 1:16,75"),
    "11": ("2:23,82 2:23,82 2:23,82 2:34,56 2:38,81", "2:55,11 2:57,30 2:50,44 2:50,10 2:49,77"),
    "13": ("32,39 32,39 32,87 34,30 35,94", "42,37 42,11 39,16 39,03 38,90"),
    "14": ("1:13,09 1:13,09 1:13,95 1:19,15 1:21,42", "1:32,89 1:32,89 1:27,55 1:26,77 1:26,00"),
    "15": ("2:44,11 2:44,11 2:45,88 2:52,18 3:01,44", "3:25,97 3:25,97 3:13,82 3:12,11 3:10,41"),
    "17": ("26,79 26,86 27,27 28,23 29,29", "33,92 33,92 32,33 32,16 32,00"),
    "18": ("1:00,31 1:00,31 1:00,31 1:03,85 1:07,00", "1:21,51 1:20,99 1:16,30 1:14,82 1:13,34"),
    "19": ("2:22,42 2:22,42 2:22,42 2:36,87 2:44,50", "3:19,27 2:54,27 2:54,27 2:54,27 2:54,27"),
    "21": ("2:22,51 2:22,51 2:23,68 2:29,21 2:32,49", "2:52,66 2:54,27 2:46,11 2:45,50 2:44,90"),
    "22": ("5:11,42 5:16,01 5:16,92 5:34,44 5:50,53", "6:16,45 6:16,45 6:04,57 5:57,39 5:50,20"),
}


def reglamento_2026() -> list[tuple[str, str, str, str, int]]:
    """Todas las marcas del reglamento: (torneo, categoría, género, event_id, ms)."""
    out = []
    for tournament, table in (("infantiles", _INFANTILES), ("interligas", _INTERLIGAS), ("interclubes", _INTERCLUBES)):
        cats = CATEGORIES[tournament]
        for event_id, (male, female) in table.items():
            m, f = male.split(), female.split()
            if tournament == "infantiles":
                male_cols, female_cols = m, f[::-1]   # M: 10..13 · F visual 13..10 → 10..13
            else:
                male_cols = m[::-1]                    # M visual mayores..14 → 14..mayores
                female_cols = f                        # F visual 14..mayores
                cats = ["14", "15", "juvb", "junior", "mayores"]
            for cat, mv, fv in zip(cats, male_cols, female_cols):
                if _t(mv) is not None:
                    out.append((tournament, cat, "M", event_id, _t(mv)))
                if _t(fv) is not None:
                    out.append((tournament, cat, "F", event_id, _t(fv)))
    return out
