"""Comandos locais: download de uma edição e extração para JSONL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from guicredito.dje.download import CADERNOS_CAPITAL, DownloadError, baixar_caderno3
from guicredito.dje.parse import iter_pdf_pages, iter_publicacoes, pagina_tem_cnj
from guicredito.dje.report import Resumo, renderizar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="guicredito")
    sub = parser.add_subparsers(dest="cmd", required=True)

    baixar = sub.add_parser("download", help="Baixa o Caderno 3 da Capital (partes I e II)")
    baixar.add_argument("--date", required=True, help="Data da edição, AAAA-MM-DD")
    baixar.add_argument("--out", default="data/raw", help="Pasta dos PDFs")

    ler = sub.add_parser("parse", help="Extrai atos dos PDFs já baixados")
    ler.add_argument("--date", required=True, help="Data da edição, AAAA-MM-DD")
    ler.add_argument("--raw", default="data/raw", help="Pasta dos PDFs")
    ler.add_argument("--out", default="data/parsed", help="Pasta do JSONL")
    ler.add_argument("--report", default="data/reports", help="Pasta do relatório")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "download":
            return _download(args.date, Path(args.out))
        return _parse(args.date, Path(args.raw), Path(args.out), Path(args.report))
    except DownloadError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _download(data: str, destino: Path) -> int:
    baixada, caminhos = baixar_caderno3(data, destino)
    if baixada != data:
        print(
            f"{data} sem edição no download do DJE. "
            f"Última edição disponível: {baixada}."
        )
    for caminho in caminhos:
        print(f"{caminho} ({caminho.stat().st_size} bytes)")
    return 0


def _parse(data: str, raw: Path, out_dir: Path, report_dir: Path) -> int:
    pdfs = [(raw / f"{data}_{codigo}.pdf", codigo) for codigo in CADERNOS_CAPITAL]
    ausentes = [str(path) for path, _ in pdfs if not path.is_file()]
    if ausentes:
        print("PDFs ausentes: " + ", ".join(ausentes), file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    jsonl = out_dir / f"{data}.jsonl"
    relatorio = report_dir / f"{data}.md"
    resumo = Resumo()

    with jsonl.open("w", encoding="utf-8") as fh:
        for path, codigo in pdfs:
            for publicacao in _publicacoes_do_pdf(path, data, codigo, resumo):
                fh.write(publicacao.model_dump_json() + "\n")

    texto = renderizar(data, resumo)
    relatorio.write_text(texto, encoding="utf-8")
    print(texto)
    print(f"JSONL: {jsonl}")
    print(f"Relatório: {relatorio}")
    return 0


def _publicacoes_do_pdf(path: Path, data: str, codigo: str, resumo: Resumo):
    def paginas():
        for numero, texto in iter_pdf_pages(path):
            resumo.paginas += 1
            if pagina_tem_cnj(texto):
                resumo.paginas_com_cnj += 1
            if resumo.paginas % 100 == 0:
                print(f"{path.name}: página {numero}", file=sys.stderr)
            yield numero, texto

    for publicacao in iter_publicacoes(paginas(), data=data, caderno=codigo):
        resumo.observar(publicacao)
        yield publicacao
