import pytest

from guicredito.djen.modelos import TipoCredor
from guicredito.djen.partes import (
    classe_de_cobranca,
    eh_empresa,
    partes_do_cabecalho,
    tipo_credor,
)


@pytest.mark.parametrize(
    "classe,esperado",
    [
        ("EXECUçãO DE TíTULO EXTRAJUDICIAL", True),
        ("CUMPRIMENTO DE SENTENçA", True),
        ("MONITóRIA", True),
        ("CUMPRIMENTO DE SENTENçA CONTRA A FAZENDA PúBLICA", False),
        ("CUMPRIMENTO DE SENTENçA DE OBRIGAçãO DE PRESTAR ALIMENTOS", False),
        ("Cumprimento de Sentença de Ações Coletivas", False),
        ("EXECUçãO FISCAL", False),
        ("EXECUçãO DA PENA", False),
        ("BUSCA E APREENSãO EM ALIENAçãO FIDUCIáRIA", False),
        ("DESPEJO POR FALTA DE PAGAMENTO CUMULADO COM COBRANçA", False),
        ("PROCEDIMENTO COMUM CíVEL", False),
        ("EMBARGOS à EXECUçãO", False),
    ],
)
def test_classe_de_cobranca(classe, esperado):
    assert classe_de_cobranca(classe) is esperado


@pytest.mark.parametrize(
    "nome,tipo",
    [
        ("BANCO SANTANDER (BRASIL) S.A.", TipoCredor.BANCO),
        ("Caixa Econômica Federal", TipoCredor.BANCO),
        ("COOPERATIVA DE CREDITO EXEMPLO - SICOOB", TipoCredor.BANCO),
        ("EXEMPLO CRÉDITO, FINANCIAMENTO E INVESTIMENTO S.A.", TipoCredor.BANCO),
        ("FIDC EXEMPLO NPL I", TipoCredor.FUNDO),
        ("EXEMPLO FUNDO DE INVESTIMENTO EM DIREITOS CREDITÓRIOS", TipoCredor.FUNDO),
        ("EXEMPLO SECURITIZADORA S.A.", TipoCredor.FUNDO),
        ("CONDOMÍNIO EDIFÍCIO EXEMPLO", TipoCredor.EMPRESA),
        ("LOJA EXEMPLO LTDA", TipoCredor.EMPRESA),
        ("JOÃO EXEMPLO DA SILVA", TipoCredor.PESSOA),
    ],
)
def test_tipo_credor(nome, tipo):
    assert tipo_credor(nome) is tipo


def test_eh_empresa():
    assert eh_empresa("LOJA EXEMPLO LTDA") and eh_empresa("MARIA MODELO ME") and eh_empresa("J. EXEMPLO EIRELI")
    assert not eh_empresa("JOÃO EXEMPLO")
    assert eh_empresa("PROMOVE EXEMPLO", "FAZ SABER a PROMOVE EXEMPLO, CNPJ: 00.000.000/0001-00, que")
    assert not eh_empresa("ANA FICTÍCIA", "intimada ANA FICTÍCIA, CPF 000.000.000-00, para")


def test_partes_do_cabecalho():
    t = (
        "EXECUÇÃO DE TÍTULO EXTRAJUDICIAL Nº 1003464-18.2022.8.26.0269/SP RELATOR : FULANO RELATOR "
        "EXEQUENTE : BANCO EXEMPLO S.A. ADVOGADO(A) : CICRANO ADVOGADO (OAB SP000000) "
        "EXECUTADO : JOÃO EXEMPLO ADVOGADO(A) : BELTRANO (OAB SP000001) ATO ORDINATÓRIO Intime-se."
    )
    assert partes_do_cabecalho(t) == (["BANCO EXEMPLO S.A."], ["JOÃO EXEMPLO"])
    assert partes_do_cabecalho("AUTOR : ANA FICTÍCIA RÉU : LOJA EXEMPLO LTDA DESPACHO Vistos.") == (
        ["ANA FICTÍCIA"],
        ["LOJA EXEMPLO LTDA"],
    )
    assert partes_do_cabecalho("Vistos. Intime-se.") == ([], [])
