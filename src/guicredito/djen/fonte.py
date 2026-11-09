import hashlib
import http.client
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

from guicredito.djen.modelos import CadernoInfo

URL_CADERNO = "https://comunicaapi.pje.jus.br/api/v1/caderno/{sigla}/{data}/D"
_BLOCO = 1024 * 1024
_USER_AGENT = "GUICredito/0.1"


class HttpErro(Exception):
    def __init__(self, status: int):
        self.status = status
        super().__init__(f"HTTP {status}")


class ErroDownload(Exception):
    pass


class ClienteHttp(Protocol):
    def get_json(self, url: str) -> dict: ...

    def baixar(self, url: str, destino: Path) -> None: ...


class ClienteUrllib:
    def __init__(self, timeout: float = 60):
        self.timeout = timeout

    def _abrir(self, url: str):
        pedido = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            return urllib.request.urlopen(pedido, timeout=self.timeout)
        except urllib.error.HTTPError as erro:
            raise HttpErro(erro.code) from erro
        except (urllib.error.URLError, TimeoutError, OSError) as erro:
            raise HttpErro(0) from erro

    def get_json(self, url: str) -> dict:
        with self._abrir(url) as resposta:
            return json.loads(resposta.read().decode())

    def baixar(self, url: str, destino: Path) -> None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._abrir(url) as resposta, destino.open("wb") as saida:
                while bloco := resposta.read(_BLOCO):
                    saida.write(bloco)
        except (TimeoutError, OSError, http.client.HTTPException) as erro:
            raise HttpErro(0) from erro


def dias_uteis(inicio: date, fim: date) -> list[date]:
    dias: list[date] = []
    dia = inicio
    while dia <= fim:
        if dia.weekday() < 5:
            dias.append(dia)
        dia += timedelta(days=1)
    return dias


def periodo_padrao(hoje: date) -> tuple[date, date]:
    dia = hoje - timedelta(days=1)
    achados: list[date] = []
    while len(achados) < 5:
        if dia.weekday() < 5:
            achados.append(dia)
        dia -= timedelta(days=1)
    achados.reverse()
    return achados[0], achados[-1]


def buscar_metadados(cliente: ClienteHttp, sigla: str, dia: date) -> CadernoInfo | None:
    url = URL_CADERNO.format(sigla=sigla, data=dia.isoformat())
    try:
        dados = cliente.get_json(url)
    except HttpErro as erro:
        if erro.status == 404:
            return None
        raise
    return CadernoInfo(
        sigla=str(dados.get("sigla_tribunal") or sigla),
        data=date.fromisoformat(str(dados.get("data") or dia.isoformat())[:10]),
        versao=int(dados["versao"]),
        total_comunicacoes=int(dados.get("total_comunicacoes") or 0),
        numero_paginas=int(dados.get("numero_paginas") or 0),
        tamanho_bytes=int(dados.get("tamanho_bytes") or 0),
        hash=str(dados["hash"]),
        url=str(dados["url"]),
    )


def _sha256(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        while bloco := arquivo.read(_BLOCO):
            resumo.update(bloco)
    return resumo.hexdigest()


def baixar_caderno(
    cliente: ClienteHttp,
    sigla: str,
    dia: date,
    pasta: Path,
    espera: Callable[[float], None] = time.sleep,
) -> tuple[CadernoInfo, Path] | None:
    pasta.mkdir(parents=True, exist_ok=True)
    motivo = "falha desconhecida"
    for tentativa in range(1, 4):
        try:
            info = buscar_metadados(cliente, sigla, dia)
        except HttpErro as erro:
            if erro.status == 404:
                return None
            motivo = f"HTTP {erro.status}"
            if tentativa < 3:
                espera(2 if tentativa == 1 else 4)
            continue
        if info is None:
            return None
        destino = pasta / f"{sigla}-D-{dia.isoformat()}_v{info.versao}.zip"
        if destino.is_file() and _sha256(destino) == info.hash.lower():
            return info, destino
        parcial = Path(str(destino) + ".part")
        try:
            cliente.baixar(info.url, parcial)
            if _sha256(parcial) != info.hash.lower():
                motivo = "hash não confere"
                parcial.unlink(missing_ok=True)
            else:
                parcial.replace(destino)
                return info, destino
        except (HttpErro, TimeoutError, OSError) as erro:
            motivo = erro.args[0] if erro.args else type(erro).__name__
            if isinstance(erro, HttpErro):
                motivo = f"HTTP {erro.status}"
            parcial.unlink(missing_ok=True)
        if tentativa < 3:
            espera(2 if tentativa == 1 else 4)
    raise ErroDownload(f"{dia.isoformat()}: {motivo}")
