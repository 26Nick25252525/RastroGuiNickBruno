"""The records the other files pass to each other. No decisions live here.

``leitura`` builds a ``Publicacao`` for one act in the gazette.
``fonte`` builds a ``CadernoInfo`` for one downloaded zip. ``casos.resumir``
turns a publication into a ``ResumoPublicacao`` (parties, signals, cited
years). ``casos.montar_casos`` folds those into one ``Caso`` per process
number. ``pontuacao`` wraps a case in ``CasoPontuado``. ``pipeline`` fills
a ``ResumoRodada`` with the counts printed at the end, and ``planilha``
reads that to write the Como ler sheet.

``TipoCredor`` and ``Bloco`` are the labels ``partes``, ``sinais`` and
``pontuacao`` share, so a bank found in one file is the same bank scored
in another.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class TipoCredor(StrEnum):
    BANCO = "Banco"
    FUNDO = "Fundo"
    PESSOA = "Pessoa"
    EMPRESA = "Empresa"


class Bloco(StrEnum):
    DESGASTE = "desgaste"
    PATRIMONIO = "patrimonio"
    VULNERABILIDADE = "vulnerabilidade"
    DESCONTO = "desconto"
    ALERTA = "alerta"


@dataclass(frozen=True)
class Destinatario:
    nome: str
    polo: str


@dataclass(frozen=True)
class Publicacao:
    id: int
    data: date
    tipo: str
    orgao: str
    numero_processo: str
    classe: str
    texto: str
    link: str
    destinatarios: tuple[Destinatario, ...]


@dataclass(frozen=True)
class CadernoInfo:
    sigla: str
    data: date
    versao: int
    total_comunicacoes: int
    numero_paginas: int
    tamanho_bytes: int
    hash: str
    url: str


@dataclass(frozen=True)
class Sinal:
    chave: str
    bloco: Bloco
    pontos: int
    rotulo: str
    trecho: str


@dataclass(frozen=True)
class Parte:
    nome: str
    empresa: bool


@dataclass(frozen=True)
class ResumoPublicacao:
    numero_processo: str
    data: date
    tipo: str
    orgao: str
    classe: str
    link: str
    credores: tuple[str, ...]
    devedores: tuple[Parte, ...]
    sinais: tuple[Sinal, ...]
    anos_citados: tuple[int, ...]


@dataclass(frozen=True)
class Caso:
    numero_processo: str
    classe: str
    orgao: str
    comarca: str
    link: str
    credor: str | None
    tipo_credor: TipoCredor | None
    devedor: str | None
    avalista: bool
    so_empresa: bool
    ano_divida: int
    sinais: tuple[Sinal, ...]
    ultima_data: date
    ultimo_tipo: str
    n_publicacoes: int


@dataclass(frozen=True)
class Pontuacao:
    credor: int
    idade: int
    desgaste: int
    patrimonio: int
    vulnerabilidade: int
    descontos: int
    total: int


@dataclass(frozen=True)
class CasoPontuado:
    caso: Caso
    pontos: Pontuacao


@dataclass
class ResumoRodada:
    inicio: date
    fim: date
    cadernos: list[CadernoInfo]
    dias_sem_caderno: list[date]
    publicacoes_lidas: int
    publicacoes_cobranca: int
    processos: int
    processos_so_empresa: int
    casos_na_planilha: int
    gerado_em: datetime
