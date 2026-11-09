from datetime import date

import pytest

from guicredito.djen.modelos import (
    Bloco,
    Caso,
    CasoPontuado,
    Pontuacao,
    Sinal,
    TipoCredor,
)
from guicredito.djen.pontuacao import ordenar, pontuar

D = Bloco.DESGASTE
P = Bloco.PATRIMONIO
V = Bloco.VULNERABILIDADE
X = Bloco.DESCONTO
A = Bloco.ALERTA


def caso(**kw) -> Caso:
    dados = dict(
        numero_processo="10034641820228260269",
        classe="EXECUÇÃO DE TÍTULO EXTRAJUDICIAL",
        orgao="1ª Vara Cível",
        comarca="São Paulo",
        link="https://exemplo/1",
        credor="BANCO EXEMPLO S.A.",
        tipo_credor=TipoCredor.BANCO,
        devedor="JOÃO EXEMPLO",
        avalista=False,
        so_empresa=False,
        ano_divida=2016,
        sinais=(),
        ultima_data=date(2026, 11, 6),
        ultimo_tipo="Intimação",
        n_publicacoes=1,
    )
    dados.update(kw)
    return Caso(**dados)


def s(chave: str, bloco: Bloco, pts: int) -> Sinal:
    return Sinal(chave, bloco, pts, chave, "trecho")


def test_exemplo_completo():
    c = caso(
        sinais=(
            s("bloqueio_negativo", D, 10),
            s("imovel_penhorado", P, 15),
            s("gratuidade_devedor", V, 8),
        )
    )
    assert pontuar(c, 2026) == Pontuacao(20, 20, 10, 15, 8, 0, 73)


@pytest.mark.parametrize(
    "ano,pts",
    [(2016, 20), (2017, 15), (2020, 15), (2021, 8), (2023, 8), (2024, 0)],
)
def test_idade(ano, pts):
    assert pontuar(caso(ano_divida=ano), 2026).idade == pts


@pytest.mark.parametrize(
    "tipo,pts",
    [
        (TipoCredor.BANCO, 20),
        (TipoCredor.FUNDO, 12),
        (TipoCredor.PESSOA, 8),
        (TipoCredor.EMPRESA, 5),
        (None, 0),
    ],
)
def test_credor(tipo, pts):
    assert pontuar(caso(tipo_credor=tipo), 2026).credor == pts


def test_tetos_por_bloco():
    p = pontuar(
        caso(
            sinais=(
                s("a", D, 10),
                s("b", D, 10),
                s("c", D, 8),
                s("d", P, 20),
                s("e", P, 15),
                s("f", V, 15),
                s("g", V, 8),
            )
        ),
        2026,
    )
    assert (p.desgaste, p.patrimonio, p.vulnerabilidade) == (25, 20, 15)


def test_descontos_e_alerta():
    p = pontuar(
        caso(
            devedor=None,
            sinais=(
                s("sem_bens", X, -10),
                s("prescricao_intercorrente", X, -10),
                s("devedor_nao_localizado", A, 0),
            ),
        ),
        2026,
    )
    assert p.descontos == -35


def test_total_nunca_negativo():
    assert (
        pontuar(
            caso(
                tipo_credor=None,
                devedor=None,
                ano_divida=2026,
                sinais=(s("sem_bens", X, -10),),
            ),
            2026,
        ).total
        == 0
    )


def test_ordenar_por_pontos_depois_ano_e_corta():
    ranked = [
        CasoPontuado(
            caso(numero_processo="10000000020208260001", ano_divida=2020),
            Pontuacao(0, 0, 0, 0, 0, 0, 80),
        ),
        CasoPontuado(
            caso(numero_processo="90000000020158260001", ano_divida=2015),
            Pontuacao(0, 0, 0, 0, 0, 0, 80),
        ),
        CasoPontuado(
            caso(numero_processo="30000000020108260001", ano_divida=2010),
            Pontuacao(0, 0, 0, 0, 0, 0, 50),
        ),
    ]
    ordenados = ordenar(ranked, 2)
    assert [(item.pontos.total, item.caso.ano_divida) for item in ordenados] == [
        (80, 2015),
        (80, 2020),
    ]
