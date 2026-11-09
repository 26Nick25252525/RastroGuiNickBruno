from guicredito.djen.texto import (
    ano_cnj,
    formatar_cnj,
    frases,
    limpar_html,
    limpar_para_excel,
    normalizar,
)

CSS = ("body{ padding: 10px; font-family: Times New Roman; font-size:13pt }; "
       "#divHeader{ line-height:25px; margin-bottom:30px }; #divBody{ max-width:90%; text-align:justify } ")


def test_limpar_html_remove_css_solto_tags_e_entidades():
    html = (f"<html><head><style>x{{}}</style></head><body>{CSS}<section><b>EXECU&Ccedil;&Atilde;O "
            "DE T&Iacute;TULO</b></section><p>Intima&ccedil;&atilde;o   realizada.</p></body></html>")
    assert limpar_html(html) == "EXECUÇÃO DE TÍTULO Intimação realizada."


def test_limpar_html_aceita_none_e_vazio():
    assert limpar_html(None) == "" and limpar_html("") == ""


def test_normalizar():
    assert normalizar("  Execução   de TÍTULO ") == "execucao de titulo"


def test_frases_nao_quebra_em_abreviacao_nem_numero():
    t = "Vistos. Suspendo nos termos do art. 921, III, do CPC. Conforme autos de n. 1030830-98.2015.8.26.0100, intime-se."
    assert frases(t) == ["Vistos.", "Suspendo nos termos do art. 921, III, do CPC.",
                         "Conforme autos de n. 1030830-98.2015.8.26.0100, intime-se."]


def test_formatar_cnj_e_ano():
    assert formatar_cnj("10034641820228260269") == "1003464-18.2022.8.26.0269"
    assert ano_cnj("10034641820228260269") == 2022
    assert ano_cnj("123") is None


def test_limpar_para_excel_remove_caracteres_de_controle():
    assert limpar_para_excel("a\x00b\x0bc\x1fd\te\nf") == "abcd\te\nf"
