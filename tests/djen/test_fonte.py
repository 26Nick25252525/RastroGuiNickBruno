import hashlib
from datetime import date

import pytest

from guicredito.djen.fonte import (
    URL_CADERNO,
    ErroDownload,
    baixar_caderno,
    dias_uteis,
    periodo_padrao,
)
from tests.djen.conftest import ClienteFalso

URL_06 = URL_CADERNO.format(sigla="TJSP", data="2026-11-06")


def meta(conteudo: bytes, versao: int = 1) -> dict:
    return {
        "tribunal": "Tribunal de Justiça do Estado de São Paulo",
        "sigla_tribunal": "TJSP",
        "meio": "D",
        "status": "Processado",
        "versao": versao,
        "data": "2026-11-06",
        "total_comunicacoes": 1,
        "numero_paginas": 1,
        "tamanho_bytes": len(conteudo),
        "hash": hashlib.sha256(conteudo).hexdigest(),
        "url": "https://s3/z",
    }


def test_dias_uteis():
    assert dias_uteis(date(2026, 11, 2), date(2026, 11, 8)) == [date(2026, 11, d) for d in (2, 3, 4, 5, 6)]


def test_periodo_padrao():
    assert periodo_padrao(date(2026, 11, 8)) == (date(2026, 11, 2), date(2026, 11, 6))
    assert periodo_padrao(date(2026, 11, 10)) == (date(2026, 11, 3), date(2026, 11, 9))


def test_sem_caderno_retorna_none(tmp_path):
    assert baixar_caderno(ClienteFalso({}, {}), "TJSP", date(2026, 11, 7), tmp_path) is None


def test_baixa_e_confere_hash(tmp_path):
    c = ClienteFalso({URL_06: meta(b"zip")}, {"https://s3/z": b"zip"})
    info, caminho = baixar_caderno(c, "TJSP", date(2026, 11, 6), tmp_path)
    assert caminho == tmp_path / "TJSP-D-2026-11-06_v1.zip" and caminho.read_bytes() == b"zip"
    assert info.versao == 1 and info.hash == hashlib.sha256(b"zip").hexdigest()


def test_usa_cache_na_segunda_vez(tmp_path):
    c = ClienteFalso({URL_06: meta(b"zip")}, {"https://s3/z": b"zip"})
    baixar_caderno(c, "TJSP", date(2026, 11, 6), tmp_path)
    baixar_caderno(c, "TJSP", date(2026, 11, 6), tmp_path)
    assert len(c.chamadas_baixar) == 1


def test_nova_versao_baixa_de_novo(tmp_path):
    (tmp_path / "TJSP-D-2026-11-06_v1.zip").write_bytes(b"velho")
    c = ClienteFalso({URL_06: meta(b"novo", versao=2)}, {"https://s3/z": b"novo"})
    _, caminho = baixar_caderno(c, "TJSP", date(2026, 11, 6), tmp_path)
    assert caminho.name == "TJSP-D-2026-11-06_v2.zip" and len(c.chamadas_baixar) == 1


def test_link_expirado_pede_metadados_de_novo(tmp_path):
    c = ClienteFalso({URL_06: meta(b"zip")}, {"https://s3/z": b"zip"}, falhas={"https://s3/z": 1})
    _, caminho = baixar_caderno(c, "TJSP", date(2026, 11, 6), tmp_path, espera=lambda s: None)
    assert caminho.exists() and len(c.chamadas_get) == 2 and not list(tmp_path.glob("*.part"))


def test_desiste_apos_3_falhas_sem_deixar_lixo(tmp_path):
    c = ClienteFalso({URL_06: meta(b"zip")}, {"https://s3/z": b"zip"}, falhas={"https://s3/z": 9})
    with pytest.raises(ErroDownload):
        baixar_caderno(c, "TJSP", date(2026, 11, 6), tmp_path, espera=lambda s: None)
    assert list(tmp_path.iterdir()) == []


def test_queda_no_meio_do_download_nao_deixa_parcial(tmp_path):
    class ClienteCai:
        def __init__(self):
            self.vezes = 0

        def get_json(self, url):
            return meta(b"zip")

        def baixar(self, url, destino):
            self.vezes += 1
            destino.write_bytes(b"parcial")
            if self.vezes < 3:
                raise TimeoutError("caiu")
            destino.write_bytes(b"zip")

    caminho_info = baixar_caderno(
        ClienteCai(), "TJSP", date(2026, 11, 6), tmp_path, espera=lambda s: None
    )
    assert caminho_info is not None
    _, caminho = caminho_info
    assert caminho.read_bytes() == b"zip"
    assert list(tmp_path.glob("*.part")) == []


def test_hash_diferente_conta_como_falha(tmp_path):
    c = ClienteFalso({URL_06: meta(b"zip")}, {"https://s3/z": b"corrompido"})
    with pytest.raises(ErroDownload):
        baixar_caderno(c, "TJSP", date(2026, 11, 6), tmp_path, espera=lambda s: None)
