import hashlib
from datetime import date, datetime

import pytest
from openpyxl import load_workbook

from guicredito.djen.fonte import URL_CADERNO
from guicredito.djen.pipeline import parse_args, rodar
from tests.djen.conftest import ClienteFalso

PROC_A = "10000011820228260001"
PROC_B = "10000021820228260002"
PROC_C = "10000031820228260003"
PROC_D = "10000041820228260004"
PROC_E = "10000051820228260005"
CNJ_A = "1000001-18.2022.8.26.0001"
CNJ_E = "1000005-18.2022.8.26.0005"


def _cliente(tmp_path, fazer_zip, dias: dict[date, list[dict]]) -> ClienteFalso:
    metadados: dict[str, dict] = {}
    arquivos: dict[str, bytes] = {}
    brutos = tmp_path / "brutos"
    brutos.mkdir()
    for dia, itens in dias.items():
        zip_path = fazer_zip(brutos, f"fonte-{dia.isoformat()}", [itens])
        conteudo = zip_path.read_bytes()
        url_zip = f"https://s3/{dia.isoformat()}"
        metadados[URL_CADERNO.format(sigla="TJSP", data=dia.isoformat())] = {
            "sigla_tribunal": "TJSP",
            "versao": 1,
            "data": dia.isoformat(),
            "total_comunicacoes": len(itens),
            "numero_paginas": 1,
            "tamanho_bytes": len(conteudo),
            "hash": hashlib.sha256(conteudo).hexdigest(),
            "url": url_zip,
        }
        arquivos[url_zip] = conteudo
    return ClienteFalso(metadados, arquivos)


def _rodar(tmp_path, cliente, inicio, fim, **kw):
    return rodar(
        inicio,
        fim,
        pasta_dados=tmp_path / "dados",
        pasta_saida=tmp_path / "saida",
        cliente=cliente,
        agora=datetime(2026, 11, 9, 12, 0),
        **kw,
    )


def test_rodar_ponta_a_ponta(tmp_path, item, fazer_zip):
    dia_06 = [
        item(
            id=1,
            numero_processo=PROC_A,
            texto="<p>A pesquisa via SISBAJUD restou infrutífera.</p>",
            destinatarios=[
                {"nome": "BANCO EXEMPLO S.A.", "polo": "A"},
                {"nome": "JOÃO EXEMPLO", "polo": "P"},
            ],
        ),
        item(
            id=2,
            numero_processo=PROC_B,
            destinatarios=[{"nome": "LOJA EXEMPLO LTDA", "polo": "P"}],
        ),
        item(
            id=3,
            numero_processo=PROC_C,
            nomeClasse="BUSCA E APREENSãO EM ALIENAçãO FIDUCIáRIA",
        ),
        item(
            id=4,
            numero_processo=PROC_D,
            nomeClasse="EXECUçãO FISCAL",
        ),
        item(
            id=5,
            numero_processo=PROC_E,
            nomeClasse="CUMPRIMENTO DE SENTENçA",
            texto="<p>Texto.</p>",
            destinatarios=[{"nome": "BANCO EXEMPLO S.A.", "polo": "A"}],
        ),
    ]
    dia_09 = [
        item(
            id=6,
            data_disponibilizacao="2026-11-09",
            numero_processo=PROC_A,
            texto="<p>Intime-se.</p>",
            destinatarios=[
                {"nome": "BANCO EXEMPLO S.A.", "polo": "A"},
                {"nome": "JOÃO EXEMPLO", "polo": "P"},
            ],
        )
    ]
    cliente = _cliente(
        tmp_path,
        fazer_zip,
        {date(2026, 11, 6): dia_06, date(2026, 11, 9): dia_09},
    )
    caminho, resumo = _rodar(tmp_path, cliente, date(2026, 11, 6), date(2026, 11, 9))
    assert caminho.is_file()
    assert resumo.publicacoes_lidas == 6
    assert resumo.publicacoes_cobranca == 4
    assert resumo.processos == 3
    assert resumo.processos_so_empresa == 1
    assert resumo.casos_na_planilha == 2

    wb = load_workbook(caminho)
    casos = wb["Casos"]
    cabecalho = [c.value for c in casos[1]]
    col_proc = cabecalho.index("Processo")
    col_pubs = cabecalho.index("Publicações no período")
    linhas = {
        row[col_proc]: (indice, row[col_pubs])
        for indice, row in enumerate(
            list(casos.iter_rows(min_row=2, values_only=True)), start=2
        )
    }
    assert linhas[CNJ_A][1] == 2
    assert linhas[CNJ_A][0] < linhas[CNJ_E][0]
    assert wb["Publicações"].max_row == 4


def test_rodar_pula_dia_sem_caderno(tmp_path, item, fazer_zip):
    cliente = _cliente(tmp_path, fazer_zip, {date(2026, 11, 6): [item(id=1)]})
    caminho, resumo = _rodar(tmp_path, cliente, date(2026, 11, 5), date(2026, 11, 6))
    assert resumo.dias_sem_caderno == [date(2026, 11, 5)]
    assert caminho.is_file()


def test_rodar_respeita_limite(tmp_path, item, fazer_zip):
    itens = [
        item(
            id=i,
            numero_processo=numero,
            destinatarios=[
                {"nome": "BANCO EXEMPLO S.A.", "polo": "A"},
                {"nome": nome, "polo": "P"},
            ],
        )
        for i, numero, nome in (
            (1, "10000061820228260006", "JOÃO EXEMPLO"),
            (2, "10000071820228260007", "ANA FICTÍCIA"),
            (3, "10000081820228260008", "CARLOS MODELO"),
        )
    ]
    cliente = _cliente(tmp_path, fazer_zip, {date(2026, 11, 6): itens})
    caminho, _resumo = _rodar(
        tmp_path, cliente, date(2026, 11, 6), date(2026, 11, 6), limite=1
    )
    assert load_workbook(caminho)["Casos"].max_row == 2


def test_parse_args():
    args = parse_args(["--inicio", "2026-11-03", "--fim", "2026-11-07"])
    assert args.inicio == date(2026, 11, 3)
    assert args.limite == 300
    assert args.tribunal == "TJSP"
    with pytest.raises(SystemExit):
        parse_args(["--inicio", "2026-11-03"])
