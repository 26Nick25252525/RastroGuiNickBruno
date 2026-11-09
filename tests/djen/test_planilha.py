from datetime import date, datetime

from openpyxl import load_workbook

from guicredito.djen.modelos import (
    Bloco,
    Caso,
    CasoPontuado,
    Pontuacao,
    Publicacao,
    ResumoRodada,
    Sinal,
    TipoCredor,
)
from guicredito.djen.planilha import escrever_planilha

NUMERO = "10034641820228260269"
LINK = "https://eproc1g.tjsp.jus.br/doc?x=1"
CABECALHO = [
    "#",
    "Pontos",
    "Processo",
    "Início",
    "Comarca",
    "Classe",
    "Credor",
    "Tipo de credor",
    "Devedor",
    "Sinais de desgaste",
    "Sinais de patrimônio",
    "Sinais de vulnerabilidade",
    "Última publicação",
    "Publicações no período",
    "Trecho principal",
]


def caso(**kw) -> Caso:
    dados = dict(
        numero_processo=NUMERO,
        classe="EXECUÇÃO DE TÍTULO EXTRAJUDICIAL",
        orgao="1ª Vara Cível da Comarca de São Bernardo do Campo",
        comarca="São Bernardo do Campo",
        link=LINK,
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


def pontuado(total: int, **kw) -> CasoPontuado:
    base = caso(**kw)
    return CasoPontuado(base, Pontuacao(0, 0, 0, 0, 0, 0, total))


def rodada(**kw) -> ResumoRodada:
    dados = dict(
        inicio=date(2026, 11, 3),
        fim=date(2026, 11, 7),
        cadernos=[],
        dias_sem_caderno=[],
        publicacoes_lidas=0,
        publicacoes_cobranca=0,
        processos=0,
        processos_so_empresa=0,
        casos_na_planilha=0,
        gerado_em=datetime(2026, 11, 8, 21, 30),
    )
    dados.update(kw)
    return ResumoRodada(**dados)


def gravar(tmp_path, casos, publicacoes=None, resumo=None):
    caminho = tmp_path / "saida" / "casos.xlsx"
    escrever_planilha(caminho, casos, publicacoes or {}, resumo or rodada())
    return load_workbook(caminho)


def test_abas_e_cabecalho(tmp_path):
    wb = gravar(tmp_path, [])
    assert wb.sheetnames == ["Casos", "Publicações", "Como ler"]
    assert [c.value for c in wb["Casos"][1]] == CABECALHO


def test_linha_do_caso(tmp_path):
    trecho = "Lavre-se o termo de penhora do imóvel."
    item = pontuado(
        73,
        avalista=True,
        sinais=(
            Sinal("bloqueio_negativo", Bloco.DESGASTE, 10, "bloqueio infrutífero", "pesquisa"),
            Sinal("imovel_penhorado", Bloco.PATRIMONIO, 15, "imóvel penhorado/avaliado", trecho),
            Sinal("sem_bens", Bloco.DESCONTO, -10, "⚠ sem bens localizados", "sem bens"),
            Sinal("devedor_nao_localizado", Bloco.ALERTA, 0, "⚠ devedor não localizado", "carta"),
        ),
    )
    wb = gravar(tmp_path, [item])
    linha = [c.value for c in wb["Casos"][2]]
    assert linha[0] == 1
    assert linha[1] == 73
    assert wb["Casos"]["B2"].fill.fgColor.rgb == "FFFFEB9C"
    assert linha[2] == "1003464-18.2022.8.26.0269"
    assert wb["Casos"]["C2"].hyperlink.target == LINK
    assert linha[8] == "JOÃO EXEMPLO [avalista/sócio]"
    assert linha[9] == "bloqueio infrutífero; ⚠ sem bens localizados; ⚠ devedor não localizado"
    assert linha[12] == "06/11 · Intimação"
    assert linha[14] == f'"{trecho}"'


def test_devedor_nao_identificado_e_fundo(tmp_path):
    wb = gravar(tmp_path, [pontuado(12, devedor=None, tipo_credor=TipoCredor.FUNDO, credor="FIDC EXEMPLO")])
    linha = [c.value for c in wb["Casos"][2]]
    assert linha[7] == "Fundo ⚑"
    assert linha[8] == "não identificado"


def test_cores_dos_pontos(tmp_path):
    wb = gravar(
        tmp_path,
        [
            pontuado(75, numero_processo="10000000020108260001"),
            pontuado(74, numero_processo="10000000020118260001"),
            pontuado(50, numero_processo="10000000020128260001"),
            pontuado(49, numero_processo="10000000020138260001"),
        ],
    )
    casos = wb["Casos"]
    assert casos["B2"].fill.fgColor.rgb == "FFC6EFCE"
    assert casos["B3"].fill.fgColor.rgb == "FFFFEB9C"
    assert casos["B4"].fill.fgColor.rgb == "FFFFEB9C"
    assert casos["B5"].fill.patternType is None


def test_texto_longo_e_caracteres_de_controle(tmp_path):
    texto = ("a" * 20000) + "\x0b" + ("b" * 19999)
    pub = Publicacao(
        id=1,
        data=date(2026, 11, 6),
        tipo="Intimação",
        orgao="1ª Vara",
        numero_processo=NUMERO,
        classe="EXECUÇÃO DE TÍTULO EXTRAJUDICIAL",
        texto=texto,
        link=LINK,
        destinatarios=(),
    )
    wb = gravar(tmp_path, [pontuado(10)], {NUMERO: [pub]})
    celula = wb["Publicações"]["E2"].value
    assert len(celula) <= 32767
    assert celula.endswith("[texto cortado]")
    assert "\x0b" not in celula


def test_como_ler_tem_periodo_e_funil(tmp_path):
    resumo = rodada(
        publicacoes_lidas=111111,
        publicacoes_cobranca=222222,
        processos=333333,
        processos_so_empresa=444444,
        casos_na_planilha=555555,
    )
    wb = gravar(tmp_path, [], resumo=resumo)
    texto = "\n".join(
        str(valor)
        for row in wb["Como ler"].iter_rows(values_only=True)
        for valor in row
        if valor is not None
    )
    assert "03/11/2026 a 07/11/2026" in texto
    for numero in (111111, 222222, 333333, 444444, 555555):
        assert str(numero) in texto
