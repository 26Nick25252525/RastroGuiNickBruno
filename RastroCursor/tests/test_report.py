from guicredito.dje.models import Advogado, Parte, Publicacao
from guicredito.dje.report import Resumo, redigir_exemplo, renderizar


def _ato() -> Publicacao:
    return Publicacao(
        data="2026-11-06",
        caderno="12",
        pagina=4,
        cnj="0001234-71.2024.8.26.0100",
        vara="1ª VARA CÍVEL",
        texto="Exequente: Alfa Ltda. Texto integral que não entra no exemplo.",
        partes=[
            Parte(papel="Exequente", nome="Alfa Ltda"),
            Parte(papel="Executado", nome="Beta Silva"),
        ],
        advogados=[Advogado(nome="Carla Dias", oab="SP 123456")],
        sinais=["execução", "penhora"],
    )


def test_exemplo_troca_nomes_por_letras():
    texto = redigir_exemplo(_ato())
    assert "Alfa Ltda" not in texto
    assert "Beta Silva" not in texto
    assert "Carla Dias" not in texto
    assert "Texto integral" not in texto
    assert "Exequente: A" in texto
    assert "Executado: B" in texto
    assert "Advogado: C (SP 123456)" in texto
    assert "1ª VARA CÍVEL" in texto


def test_relatorio_conta_sinais_e_cinco_exemplos_no_maximo():
    resumo = Resumo()
    for indice in range(7):
        ato = _ato()
        ato.cnj = f"000123{indice}-71.2024.8.26.0100"
        if indice == 3:
            ato.sinais = []
            ato.nomes = ["Nome Solto"]
        resumo.observar(ato)
    texto = renderizar("2026-11-06", resumo)
    assert "Publicações: 7" in texto
    assert "Com papel rotulado: 7" in texto
    assert "Com nome solto: 1" in texto
    assert "execução: 6" in texto
    assert "### 5" in texto
    assert "### 6" not in texto
