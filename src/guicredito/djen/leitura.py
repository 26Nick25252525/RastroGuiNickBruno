"""Turn one downloaded caderno zip into publications.

``fonte.py`` saves the zip. This file opens it. Each zip holds JSON files,
and each JSON file holds a list called ``items``. One item is one act in
the gazette. ``ler_caderno`` walks those items and yields a ``Publicacao``
for each one that is still active. An item with ``ativo`` false, or with a
cancellation date, is skipped. ``_publicacao`` copies the fields the rest
of the pipeline needs (date, court, case number, class, link, parties) and
strips the HTML out of the text. Nothing here filters by class or score.
That happens later, in ``pipeline.py``.
"""

import json
import zipfile
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from guicredito.djen.modelos import Destinatario, Publicacao
from guicredito.djen.texto import limpar_html


def ler_caderno(caminho_zip: Path) -> Iterator[Publicacao]:
    with zipfile.ZipFile(caminho_zip) as arquivo:
        for nome in arquivo.namelist():
            if not nome.endswith(".json"):
                continue
            dados = json.loads(arquivo.read(nome))
            for item in dados.get("items", []):
                if item.get("ativo") is False:
                    continue
                if item.get("data_cancelamento"):
                    continue
                yield _publicacao(item)


def _publicacao(item: dict) -> Publicacao:
    bruto = item.get("destinatarios") or []
    destinatarios = tuple(
        Destinatario(str(d.get("nome") or ""), str(d.get("polo") or ""))
        for d in bruto
    )
    data_txt = str(item.get("data_disponibilizacao") or "1970-01-01")
    return Publicacao(
        id=int(item.get("id") or 0),
        data=date.fromisoformat(data_txt[:10]),
        tipo=str(item.get("tipoComunicacao") or ""),
        orgao=str(item.get("nomeOrgao") or ""),
        numero_processo=str(item.get("numero_processo") or ""),
        classe=str(item.get("nomeClasse") or ""),
        texto=limpar_html(item.get("texto")),
        link=str(item.get("link") or ""),
        destinatarios=destinatarios,
    )
