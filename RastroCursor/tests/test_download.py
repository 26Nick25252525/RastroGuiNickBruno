import pytest

from datetime import date, timedelta

from guicredito.dje.download import (
    CADERNOS_CAPITAL,
    DownloadError,
    parametros_data,
    parece_pdf,
    ultima_data_com_edicao,
)


def test_cadernos_da_capital():
    assert CADERNOS_CAPITAL == ("12", "20")


def test_parametros_data_tenta_iso_e_depois_br():
    assert parametros_data("2026-11-06") == ["2026-11-06", "06/11/2026"]


def test_data_invalida():
    with pytest.raises(DownloadError):
        parametros_data("06/11/2026")


def test_parece_pdf():
    assert parece_pdf(b"%PDF-1.7\n")
    assert not parece_pdf(b"<html>sem edicao</html>")


def test_ultima_edicao_para_quando_o_acervo_acaba():
    limite = date(2025, 7, 22)

    def tem(dia: date) -> bool:
        return dia <= limite and dia.weekday() < 5

    assert ultima_data_com_edicao(date(2007, 10, 1), date(2026, 11, 6), tem) == limite


def test_ultima_edicao_devolve_a_data_pedida_se_ela_existe():
    pedida = date(2026, 11, 6)
    assert pedida.weekday() < 5
    assert ultima_data_com_edicao(pedida - timedelta(days=10), pedida, lambda dia: dia == pedida) == pedida
