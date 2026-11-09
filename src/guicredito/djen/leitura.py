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
