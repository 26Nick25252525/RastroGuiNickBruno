from guicredito.dje.parse import (
    cnj_valido,
    extrair_advogados,
    extrair_partes,
    extrair_sinais,
    iter_publicacoes,
)

CNJ_A = "0001234-71.2024.8.26.0100"
CNJ_B = "0009876-67.2023.8.26.0100"
CNJ_C = "1045678-57.2025.8.26.0224"
CNJ_INVALIDO = "0001234-00.2024.8.26.0100"


def _atos(texto: str, pagina: int = 1):
    return list(
        iter_publicacoes([(pagina, texto)], data="2026-11-06", caderno="12")
    )


def test_cnj_valido_rejeita_digito_errado():
    assert cnj_valido(CNJ_A)
    assert not cnj_valido(CNJ_INVALIDO)


def test_extrai_partes_advogado_e_sinais():
    texto = (
        f"Processo {CNJ_A} - Execução de Título Extrajudicial - "
        "Exequente: Alfa Ltda - Executado: Beta Comércio Ltda - "
        "Advogado: Carla Dias - OAB/SP 123456 - "
        "Vistos. Cite-se. Penhora do imóvel da executada."
    )
    atos = _atos(texto)
    assert len(atos) == 1
    ato = atos[0]
    assert ato.cnj == CNJ_A
    assert ato.pagina == 1
    assert [(p.papel, p.nome) for p in ato.partes] == [
        ("Exequente", "Alfa Ltda"),
        ("Executado", "Beta Comércio Ltda"),
    ]
    assert ato.advogados[0].nome == "Carla Dias"
    assert ato.advogados[0].oab == "SP 123456"
    assert "execução" in ato.sinais
    assert "citação" in ato.sinais
    assert "penhora" in ato.sinais
    assert "acordo" not in ato.sinais


def test_abreviacoes_e_acordo():
    texto = (
        f"Processo {CNJ_C} - Cumprimento de sentença\n"
        "Exeqte: Nome Um\n"
        "Exectdo: Nome Dois\n"
        "Acordo homologado."
    )
    ato = _atos(texto)[0]
    assert [p.papel for p in ato.partes] == ["Exequente", "Executado"]
    assert [p.nome for p in ato.partes] == ["Nome Um", "Nome Dois"]
    assert "cumprimento de sentença" in ato.sinais
    assert "acordo" in ato.sinais
    assert "homologação" in ato.sinais


def test_nomes_soltos_quando_nao_ha_rotulo():
    texto = (
        f"Processo {CNJ_B} - Procedimento Comum Cível - "
        "Maria Clara Souza - José Lima - Intimação expedida."
    )
    ato = _atos(texto)[0]
    assert ato.partes == []
    assert ato.nomes == ["Maria Clara Souza", "José Lima"]


def test_titulo_de_secao_nao_vira_vara():
    texto = (
        "RELAÇÃO DOS FEITOS CÍVEIS DISTRIBUÍDOS ÀS VARAS DO FORO CENTRAL CÍVEL EM 20/07/2025\n"
        "  PROCESSO   :1100472-12.2025.8.26.0100\n"
        "   EXEQTE           : Marcos Pereira\n"
        "   VARA: V. U. - RECURSO INOMINADO DO RÉU - JUIZADO ESPECIAL CÍVEL - PEDIDO DE DESISTÊNCIA\n"
        "   VARA:37ª VARA CÍVEL\n"
    )
    ato = _atos(texto)[0]
    assert ato.vara == "37ª VARA CÍVEL"


def test_vara_e_dois_atos():
    texto = (
        "FORO CENTRAL CÍVEL\n"
        "1ª VARA CÍVEL\n"
        f"Processo {CNJ_A} - Exequente: Alfa Ltda - Executado: Beta Silva\n"
        "2ª VARA CÍVEL\n"
        f"Processo {CNJ_B} - Autor: Carla Dias - Réu: Diego Costa\n"
    )
    atos = _atos(texto)
    assert [a.cnj for a in atos] == [CNJ_A, CNJ_B]
    assert atos[0].vara == "1ª VARA CÍVEL"
    assert atos[1].vara == "2ª VARA CÍVEL"
    assert atos[1].partes[0].papel == "Autor"
    assert atos[1].partes[1].papel == "Réu"


def test_numero_invalido_nao_abre_ato():
    assert _atos(f"Valor  {CNJ_INVALIDO} sem processo.") == []


def test_nao_cria_campo_de_documento():
    texto = f"Processo {CNJ_A} - Exequente: Alfa Ltda - CPF 123.456.789-00"
    ato = _atos(texto)[0]
    chaves = set(ato.model_dump())
    assert "cpf" not in chaves
    assert "documento" not in chaves
    assert "123.456.789-00" in ato.texto


def test_lista_de_distribuicao_do_caderno():
    texto = (
        "  PROCESSO   :1100472-12.2025.8.26.0100\n"
        "   CLASSE     :EXECUÇÃO DE TÍTULO EXTRAJUDICIAL\n"
        "   EXEQTE           : Marcos Pereira\n"
        "  ADVOGADO    : 120617/SP - Nilton Pires\n"
        "  EXECTDO        : Kaufen Car Ltda\n"
        "   VARA:37ª VARA CÍVEL\n"
        "  REQDO            : sobra da página anterior\n"
        "  PROCESSO   :1053815-15.2025.8.26.0002\n"
        "   CLASSE     :EXECUÇÃO DE TÍTULO EXTRAJUDICIAL\n"
        "   EXEQTE           : Marcia Maria Muller\n"
        "   EXECTDA        : Cristiane Bezerra\n"
        "   VARA:7ª VARA CÍVEL\n"
    )
    atos = _atos(texto)
    assert [a.cnj for a in atos] == [
        "1100472-12.2025.8.26.0100",
        "1053815-15.2025.8.26.0002",
    ]
    primeiro = atos[0]
    assert primeiro.vara == "37ª VARA CÍVEL"
    assert [(p.papel, p.nome) for p in primeiro.partes] == [
        ("Exequente", "Marcos Pereira"),
        ("Executado", "Kaufen Car Ltda"),
        ("Requerido", "sobra da página anterior"),
    ]
    assert primeiro.advogados[0].nome == "Nilton Pires"
    assert primeiro.advogados[0].oab == "SP 120617"
    assert "execução" in primeiro.sinais
    assert atos[1].partes[1].papel == "Executado"
    assert "sobra da página anterior" in primeiro.texto


def test_ato_em_prosa_nao_quebra_no_cnj_repetido():
    cnj = "0005646-25.2024.8.26.0624"
    texto = (
        f"{cnj}; Processo Digital; Recorrente: Prefeitura Municipal de Tatuí; "
        "Advogado: Luiz Carlos Prado (OAB: 151797/SP); Recorrida: Terezinha de Fátima; "
        f"{cnj}; intimação expedida."
    )
    atos = _atos(texto)
    assert len(atos) == 1
    assert [p.papel for p in atos[0].partes] == ["Recorrente", "Recorrido"]
    assert atos[0].advogados[0].nome == "Luiz Carlos Prado"
    assert atos[0].advogados[0].oab == "SP 151797"


def test_partes_e_advogados_isolados():
    texto = "Exequente: Alfa Ltda - Advogado: Carla Dias OAB/SP 123.456"
    assert extrair_partes(texto)[0].nome == "Alfa Ltda"
    advogado = extrair_advogados(texto)[0]
    assert advogado.nome == "Carla Dias"
    assert advogado.oab == "SP 123456"
    assert extrair_sinais("Penhora e arresto") == ["penhora", "arresto"]
