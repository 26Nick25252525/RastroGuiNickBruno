from pathlib import Path

import pytest

from guicredito.dje.parse import cnj_valido, iter_pdf_pages, iter_publicacoes

RAIZ = Path(__file__).resolve().parents[1]


def _pdf_da_edicao() -> Path | None:
    achados = sorted((RAIZ / "data" / "raw").glob("*_12.pdf"))
    return achados[-1] if achados else None


def test_pdf_da_edicao_abre_como_texto_e_tem_cnj():
    pdf = _pdf_da_edicao()
    if pdf is None:
        pytest.skip("PDF da edição não está em data/raw")
    data = pdf.name.split("_", 1)[0]

    paginas: list[tuple[int, str]] = []
    caracteres = 0
    for numero, texto in iter_pdf_pages(pdf):
        paginas.append((numero, texto))
        caracteres += len(texto.strip())
        if numero >= 40:
            break

    assert paginas
    assert caracteres / len(paginas) > 100
    atos = list(iter_publicacoes(paginas, data=data, caderno="12"))
    assert atos
    assert all(cnj_valido(ato.cnj) for ato in atos)
