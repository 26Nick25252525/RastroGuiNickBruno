"""Contagens da edição e exemplos com nomes trocados por letras."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from guicredito.dje.models import Publicacao

SINAIS = (
    "execução",
    "cumprimento de sentença",
    "penhora",
    "citação",
    "acordo",
    "transação",
    "homologação",
    "hasta",
    "adjudicação",
    "avaliação",
    "arresto",
)
_LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@dataclass
class Resumo:
    publicacoes: int = 0
    paginas: int = 0
    paginas_com_cnj: int = 0
    cnjs: set[str] = field(default_factory=set)
    com_papel: int = 0
    com_nome_solto: int = 0
    sinais: Counter[str] = field(default_factory=Counter)
    exemplos: list[str] = field(default_factory=list)

    def observar(self, publicacao: Publicacao) -> None:
        self.publicacoes += 1
        self.cnjs.add(publicacao.cnj)
        if publicacao.partes:
            self.com_papel += 1
        if publicacao.nomes:
            self.com_nome_solto += 1
        for sinal in publicacao.sinais:
            self.sinais[sinal] += 1
        if len(self.exemplos) < 5 and publicacao.sinais:
            self.exemplos.append(redigir_exemplo(publicacao))


def redigir_exemplo(publicacao: Publicacao) -> str:
    mapa: dict[str, str] = {}

    def letra(nome: str) -> str:
        if nome not in mapa:
            mapa[nome] = _LETRAS[len(mapa) % len(_LETRAS)]
        return mapa[nome]

    linhas = [
        f"CNJ {publicacao.cnj} · caderno {publicacao.caderno} · p. {publicacao.pagina}"
    ]
    if publicacao.vara:
        linhas.append(f"Vara: {publicacao.vara}")
    for parte in publicacao.partes:
        linhas.append(f"{parte.papel}: {letra(parte.nome)}")
    for nome in publicacao.nomes:
        linhas.append(f"Nome: {letra(nome)}")
    for advogado in publicacao.advogados:
        quem = letra(advogado.nome) if advogado.nome else "?"
        oab = f" ({advogado.oab})" if advogado.oab else ""
        linhas.append(f"Advogado: {quem}{oab}")
    if publicacao.sinais:
        linhas.append("Sinais: " + ", ".join(publicacao.sinais))
    return "\n".join(linhas)


def renderizar(data: str, resumo: Resumo) -> str:
    linhas = [
        f"# DJE Caderno 3 — edição {data}",
        "",
        f"- Publicações: {resumo.publicacoes}",
        f"- Números CNJ distintos: {len(resumo.cnjs)}",
        f"- Páginas lidas: {resumo.paginas}",
        f"- Páginas com CNJ: {resumo.paginas_com_cnj}",
        f"- Com papel rotulado: {resumo.com_papel}",
        f"- Com nome solto: {resumo.com_nome_solto}",
        "",
        "## Sinais",
        "",
    ]
    for sinal in SINAIS:
        linhas.append(f"- {sinal}: {resumo.sinais.get(sinal, 0)}")
    linhas.extend(["", "## Exemplos", ""])
    if not resumo.exemplos:
        linhas.append("Nenhuma publicação com sinal nesta edição.")
    for indice, exemplo in enumerate(resumo.exemplos, start=1):
        linhas.append(f"### {indice}")
        linhas.append("")
        linhas.append(exemplo)
        linhas.append("")
    return "\n".join(linhas).rstrip() + "\n"
