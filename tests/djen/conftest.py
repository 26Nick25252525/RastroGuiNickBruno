import json
import zipfile
from pathlib import Path

import pytest


def _item(**alteracoes) -> dict:
    base = {
        "id": 1,
        "data_disponibilizacao": "2026-11-06",
        "tipoComunicacao": "Intimação",
        "nomeOrgao": "UPJ da 1ª a 4ª Varas Civeis da Comarca de Itapetininga",
        "texto": "<p>Texto.</p>",
        "numero_processo": "10034641820228260269",
        "link": "https://eproc1g.tjsp.jus.br/doc?x=1",
        "nomeClasse": "EXECUçãO DE TíTULO EXTRAJUDICIAL",
        "ativo": True,
        "data_cancelamento": None,
        "destinatarios": [{"nome": "BANCO EXEMPLO S.A.", "polo": "A"}],
    }
    base.update(alteracoes)
    return base


def _fazer_zip(pasta: Path, nome_base: str, arquivos: list[list[dict]]) -> Path:
    caminho = pasta / f"{nome_base}.zip"
    with zipfile.ZipFile(caminho, "w") as arquivo:
        for indice, itens in enumerate(arquivos, start=1):
            payload = {"count": len(itens), "items": itens}
            nome = f"{nome_base}_{indice}.json"
            arquivo.writestr(nome, json.dumps(payload, ensure_ascii=False))
    return caminho


@pytest.fixture
def item():
    return _item


@pytest.fixture
def fazer_zip():
    return _fazer_zip
