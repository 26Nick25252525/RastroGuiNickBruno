"""Baixa o Caderno 3 pelo botão oficial de download do DJE."""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

import httpx

INDEX_URL = "https://dje.tjsp.jus.br/cdje/index.do"
DOWNLOAD_URL = "https://dje.tjsp.jus.br/cdje/downloadCaderno.do"
CADERNOS_CAPITAL = ("12", "20")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


class DownloadError(RuntimeError):
    pass


def parametros_data(iso: str) -> list[str]:
    """O formulário atual manda AAAA-MM-DD; links antigos usam DD/MM/AAAA."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", iso):
        raise DownloadError(f"Data inválida: {iso}. Use AAAA-MM-DD.")
    ano, mes, dia = iso.split("-")
    return [iso, f"{dia}/{mes}/{ano}"]


def parece_pdf(blob: bytes) -> bool:
    return b"%PDF" in blob[:16]


def pdf_valido(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 1024:
        return False
    with path.open("rb") as fh:
        return parece_pdf(fh.read(16))


def ultima_data_com_edicao(
    inicio: date,
    fim: date,
    tem: Callable[[date], bool],
    janela: int = 800,
) -> date | None:
    """Último dia útil com edição, andando para trás a partir de fim."""
    dia = fim
    limite = max(inicio, fim - timedelta(days=janela))
    while dia >= limite:
        if dia.weekday() < 5 and tem(dia):
            return dia
        dia -= timedelta(days=1)
    return None


def baixar_caderno3(iso: str, diretorio: Path) -> tuple[str, list[Path]]:
    """Baixa a edição pedida, ou a última disponível se essa data não tiver caderno.

    Devolve a data efetivamente baixada e os dois PDFs.
    """
    diretorio = Path(diretorio)
    diretorio.mkdir(parents=True, exist_ok=True)
    pedida = _data_iso(iso)
    timeout = httpx.Timeout(30.0, read=600.0)
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(follow_redirects=True, headers=headers, timeout=timeout) as client:
        index = client.get(INDEX_URL)
        index.raise_for_status()
        escolhida = pedida if _tem_edicao(client, pedida) else _resolver_ultima(client, pedida)
        if escolhida is None:
            raise DownloadError(f"Nenhuma edição do Caderno 3 disponível até {iso}.")
        iso_escolhida = escolhida.isoformat()
        caminhos = [
            _baixar_um(
                client,
                codigo,
                iso_escolhida,
                diretorio / f"{iso_escolhida}_{codigo}.pdf",
            )
            for codigo in CADERNOS_CAPITAL
        ]
        return iso_escolhida, caminhos


def _data_iso(iso: str) -> date:
    parametros_data(iso)
    ano, mes, dia = (int(p) for p in iso.split("-"))
    return date(ano, mes, dia)


def _tem_edicao(client: httpx.Client, dia: date) -> bool:
    iso = dia.isoformat()
    return any(parece_pdf(_primeiro_bloco(client, param, "12")) for param in parametros_data(iso))


def _resolver_ultima(client: httpx.Client, pedida: date) -> date | None:
    piso = date(2007, 10, 1)
    consultas = 0

    def tem(dia: date) -> bool:
        nonlocal consultas
        consultas += 1
        if consultas % 25 == 0:
            print(f"procurando edição… {dia.isoformat()}", file=sys.stderr)
        param = dia.strftime("%d/%m/%Y")
        return parece_pdf(_primeiro_bloco(client, param, "12"))

    return ultima_data_com_edicao(piso, pedida, tem)


def _primeiro_bloco(client: httpx.Client, param: str, codigo: str) -> bytes:
    try:
        with client.stream(
            "GET",
            _url(param, codigo),
            headers={"Referer": INDEX_URL},
        ) as resp:
            resp.raise_for_status()
            return next(resp.iter_bytes(chunk_size=4096), b"")
    except httpx.HTTPError:
        return b""


def _url(param: str, codigo: str) -> str:
    return f"{DOWNLOAD_URL}?dtDiario={param}&cdCaderno={codigo}&tpDownload=D"


def _baixar_um(client: httpx.Client, codigo: str, iso: str, destino: Path) -> Path:
    if pdf_valido(destino):
        return destino
    erros: list[str] = []
    for param in parametros_data(iso):
        baixou = _tentar(client, codigo, param, destino, erros)
        if baixou:
            return destino
    raise DownloadError(
        f"Caderno {codigo} em {iso} não veio como PDF. " + " | ".join(erros)
    )


def _tentar(
    client: httpx.Client,
    codigo: str,
    param: str,
    destino: Path,
    erros: list[str],
) -> bool:
    tmp = destino.with_suffix(".part")
    try:
        with client.stream(
            "GET",
            _url(param, codigo),
            headers={"Referer": INDEX_URL},
        ) as resp:
            resp.raise_for_status()
            iterator = resp.iter_bytes(chunk_size=64 * 1024)
            try:
                first = next(iterator)
            except StopIteration:
                erros.append(f"{param}: resposta vazia")
                return False
            if not parece_pdf(first):
                erros.append(f"{param}: {_resumo(first)}")
                return False
            with tmp.open("wb") as fh:
                fh.write(first)
                for chunk in iterator:
                    fh.write(chunk)
    except httpx.HTTPError as exc:
        tmp.unlink(missing_ok=True)
        erros.append(f"{param}: {exc.__class__.__name__}")
        return False
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(destino)
    return True


def _resumo(blob: bytes) -> str:
    texto = blob[:800].decode("utf-8", errors="replace")
    paragrafo = re.search(r"<p[^>]*>(.*?)</p>", texto, re.DOTALL)
    if paragrafo:
        texto = paragrafo.group(1)
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto[:180] or "resposta sem PDF"
