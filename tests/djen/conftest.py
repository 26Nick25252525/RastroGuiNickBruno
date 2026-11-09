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


class ClienteFalso:
    def __init__(
        self,
        metadados: dict[str, dict | None],
        arquivos: dict[str, bytes],
        falhas: dict[str, int] | None = None,
    ):
        self.metadados = metadados
        self.arquivos = arquivos
        self.falhas = dict(falhas or {})
        self.chamadas_get: list[str] = []
        self.chamadas_baixar: list[str] = []

    def get_json(self, url: str) -> dict:
        from guicredito.djen.fonte import HttpErro

        self.chamadas_get.append(url)
        if url not in self.metadados or self.metadados[url] is None:
            raise HttpErro(404)
        return self.metadados[url]

    def baixar(self, url: str, destino: Path) -> None:
        from guicredito.djen.fonte import HttpErro

        self.chamadas_baixar.append(url)
        if self.falhas.get(url, 0) > 0:
            self.falhas[url] -= 1
            raise HttpErro(403)
        if url not in self.arquivos or self.arquivos[url] is None:
            raise HttpErro(404)
        destino.write_bytes(self.arquivos[url])
