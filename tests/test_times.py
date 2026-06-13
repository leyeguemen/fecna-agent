import pytest

from fecna_agent.times import diff_seconds, ms_to_time, time_to_ms


def test_time_to_ms_ejemplos_del_spec():
    assert time_to_ms("00:00:28.84") == 28840
    assert time_to_ms("00:01:02.15") == 62150


def test_time_to_ms_con_horas():
    assert time_to_ms("01:00:00.00") == 3_600_000


def test_time_to_ms_invalido():
    with pytest.raises(ValueError):
        time_to_ms("28.84")


def test_ms_to_time_inverso():
    assert ms_to_time(28840) == "00:00:28.84"
    assert ms_to_time(62150) == "00:01:02.15"


def test_diff_seconds():
    assert diff_seconds(28840, 29680) == pytest.approx(0.84)
