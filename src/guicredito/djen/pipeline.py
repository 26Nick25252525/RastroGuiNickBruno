import argparse
import sys
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path

from guicredito.djen.casos import montar_casos, resumir
from guicredito.djen.fonte import ClienteHttp, ClienteUrllib, baixar_caderno, dias_uteis, periodo_padrao
from guicredito.djen.leitura import ler_caderno
from guicredito.djen.modelos import CasoPontuado, Publicacao, ResumoRodada
from guicredito.djen.partes import classe_de_cobranca
from guicredito.djen.planilha import escrever_planilha
from guicredito.djen.pontuacao import ordenar, pontuar


def rodar(
    inicio: date,
    fim: date,
    *,
    sigla: str = "TJSP",
    limite: int = 300,
    pasta_dados: Path = Path("dados/cadernos"),
    pasta_saida: Path = Path("saida"),
    cliente: ClienteHttp | None = None,
    agora: datetime | None = None,
) -> tuple[Path, ResumoRodada]:
    http = cliente or ClienteUrllib()
    momento = agora or datetime.now()
    cadernos = []
    dias_sem_caderno: list[date] = []
    for dia in dias_uteis(inicio, fim):
        baixado = baixar_caderno(http, sigla, dia, pasta_dados)
        if baixado is None:
            dias_sem_caderno.append(dia)
            print(f"sem caderno em {dia:%d/%m}")
            continue
        cadernos.append(baixado)

    publicacoes_lidas = 0
    publicacoes_cobranca = 0
    resumos = []
    for _info, caminho in cadernos:
        for pub in ler_caderno(caminho):
            publicacoes_lidas += 1
            if classe_de_cobranca(pub.classe):
                publicacoes_cobranca += 1
                resumos.append(resumir(pub))

    casos = montar_casos(resumos)
    so_empresa = [caso for caso in casos if caso.so_empresa]
    pontuados = [
        CasoPontuado(caso, pontuar(caso, momento.year))
        for caso in casos
        if not caso.so_empresa
    ]
    escolhidos = ordenar(pontuados, limite)
    numeros = {item.caso.numero_processo for item in escolhidos}
    publicacoes = _publicacoes_dos_casos(cadernos, numeros)

    caminho = pasta_saida / f"casos_djen_{inicio:%Y-%m-%d}_a_{fim:%Y-%m-%d}.xlsx"
    resumo = ResumoRodada(
        inicio=inicio,
        fim=fim,
        cadernos=[info for info, _caminho in cadernos],
        dias_sem_caderno=dias_sem_caderno,
        publicacoes_lidas=publicacoes_lidas,
        publicacoes_cobranca=publicacoes_cobranca,
        processos=len(casos),
        processos_so_empresa=len(so_empresa),
        casos_na_planilha=len(escolhidos),
        gerado_em=momento,
    )
    escrever_planilha(caminho, escolhidos, publicacoes, resumo)
    return caminho, resumo


def _publicacoes_dos_casos(
    cadernos: Iterable[tuple[object, Path]],
    numeros: set[str],
) -> dict[str, list[Publicacao]]:
    publicacoes: dict[str, list[Publicacao]] = {numero: [] for numero in numeros}
    for _info, caminho in cadernos:
        for pub in ler_caderno(caminho):
            if pub.numero_processo in numeros:
                publicacoes[pub.numero_processo].append(pub)
    return publicacoes


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="guicredito.djen")
    parser.add_argument("--inicio", help="AAAA-MM-DD")
    parser.add_argument("--fim", help="AAAA-MM-DD")
    parser.add_argument("--limite", type=int, default=300)
    parser.add_argument("--tribunal", default="TJSP")
    args = parser.parse_args(argv)
    if (args.inicio is None) != (args.fim is None):
        parser.error("informe --inicio e --fim juntos, ou nenhum dos dois")
    if args.inicio is None:
        args.inicio, args.fim = periodo_padrao(date.today())
    else:
        args.inicio = date.fromisoformat(args.inicio)
        args.fim = date.fromisoformat(args.fim)
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    caminho, resumo = rodar(
        args.inicio,
        args.fim,
        sigla=args.tribunal,
        limite=args.limite,
        cliente=ClienteUrllib(),
    )
    print(f"Dias com caderno: {len(resumo.cadernos)} (sem caderno: {len(resumo.dias_sem_caderno)})")
    print(f"Publicações lidas: {resumo.publicacoes_lidas}")
    print(f"Publicações de cobrança: {resumo.publicacoes_cobranca}")
    print(
        f"Processos: {resumo.processos} "
        f"(só empresa, fora da planilha: {resumo.processos_so_empresa})"
    )
    print(f"Casos na planilha: {resumo.casos_na_planilha}")
    print(f"Planilha: {caminho}")
    return 0
