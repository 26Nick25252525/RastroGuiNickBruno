"""Extrai atos do texto do Caderno 3."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator
from pathlib import Path

from guicredito.dje.models import Advogado, Parte, Publicacao

CNJ_RE = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")

_ROLES: tuple[tuple[str, str], ...] = (
    ("Exequente", r"Exequentes?|Exeqtes?"),
    ("Executado", r"Executad[oa]s?|Exectd[oa]s?"),
    ("Embargante", r"Embargantes?"),
    ("Embargado", r"Embargad[oa]s?"),
    ("Requerente", r"Requerentes?|Reqtes?"),
    ("Requerido", r"Requerid[oa]s?|Reqd[oa]s?"),
    ("Recorrente", r"Recorrentes?"),
    ("Recorrido", r"Recorrid[oa]s?"),
    ("Credor", r"Credores|Credoras|Credor|Credora"),
    ("Devedor", r"Devedores|Devedoras|Devedor|Devedora"),
    ("Autor", r"Autores|Autoras|Autor|Autora"),
    ("Réu", r"R[ée]us|R[ée]u"),
)
_ROLE_ALT = "|".join(pat for _, pat in _ROLES)
_ROLE_CANON = tuple(
    (re.compile(rf"^(?:{pat})$", re.IGNORECASE), canon) for canon, pat in _ROLES
)

_NAME_END = (
    rf"(?=\s+-\s+|\s+(?:{_ROLE_ALT})\s*:|\s+Advogad|\.\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ]|\n|$)"
)
PARTY_RE = re.compile(
    rf"(?<![A-Za-zÀ-ÿ])(?P<role>{_ROLE_ALT})\s*:\s*(?P<name>.{{2,160}}?){_NAME_END}",
    re.IGNORECASE,
)
LAWYER_RE = re.compile(
    r"Advogad[oa]s?\s*:\s*(?P<body>.{2,200}?)(?=\s+-\s+(?!OAB\b)|\n|$)",
    re.IGNORECASE,
)
OAB_RE = re.compile(
    r"OAB\s*/?\s*(?P<uf>[A-Za-z]{2})?\s*[:\-]?\s*(?P<num>\d{1,3}\.?\d{3}|\d{4,6})",
    re.IGNORECASE,
)
_DIST_ADV_RE = re.compile(
    r"(?im)^ADVOGAD[OA]S?\s*:\s*(?P<num>\d{3,6})\s*/\s*(?P<uf>[A-Za-z]{2})\s*-\s*(?P<nome>.+?)\s*$"
)
_PROSE_ADV_RE = re.compile(
    r"Advogad[oa]s?\s*:\s*(?P<nome>[^(\n]{2,160}?)\s*\(\s*OAB\s*:\s*(?P<num>\d+)\s*/\s*(?P<uf>[A-Za-z]{2})\s*\)",
    re.IGNORECASE,
)
_VARA_RE = re.compile(r"(?im)^\s*VARA\s*:\s*(?P<vara>.+?)\s*$")

_SIGNALS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("execução", re.compile(r"execuc")),
    ("cumprimento de sentença", re.compile(r"cumprimento de sentenca")),
    ("penhora", re.compile(r"penhor")),
    ("citação", re.compile(r"citacao|cite-se|cita-se|citad")),
    ("acordo", re.compile(r"acordos?")),
    ("transação", re.compile(r"transacao")),
    ("homologação", re.compile(r"homolog")),
    ("hasta", re.compile(r"hasta")),
    ("adjudicação", re.compile(r"adjudic")),
    ("avaliação", re.compile(r"avalia")),
    ("arresto", re.compile(r"arrest")),
)

COURT_RE = re.compile(
    r"\b(vara|foro|juizado|ju[ií]z[oa]|juizo|distribui)\b",
    re.IGNORECASE,
)
FOOTER_RE = re.compile(
    r"di[aá]rio da justi[cç]a|publica[cç][aã]o oficial|caderno\s+\d|www\.tjsp|"
    r"disponibiliza[cç][aã]o|^s[aã]o paulo,\s|tribunal de justi[cç]a",
    re.IGNORECASE,
)
CLASS_HINT = re.compile(
    r"\b(t[ií]tulo|procedimento|cumprimento|execu[cç][aã]o de|c[ií]vel|"
    r"senten[cç]a|monit[oó]ria|despejo|usucapi[aã]o|busca e apreens|"
    r"presta[cç][aã]o|processo|vistos|intime-se|cite-se|certifico|"
    r"conclusos|fls|intima[cç][aã]o|cita[cç][aã]o)\b",
    re.IGNORECASE,
)
_PREAMBLE_END = re.compile(
    r"\b(Vistos|Intime-se|Cite-se|Certifico|Conclusos)\b",
    re.IGNORECASE,
)
_COMPANY = re.compile(r"\b(ltda|s\.?\s?a\.?|s/a|eireli|epp)\b", re.IGNORECASE)
_PARTICLES = {"de", "da", "do", "dos", "das", "e"}
_WORD = re.compile(r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç'-]+")


def dobrar(texto: str) -> str:
    base = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(c for c in base if unicodedata.category(c) != "Mn")
    return sem_acento.lower()


def cnj_valido(numero: str) -> bool:
    match = re.fullmatch(r"(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})", numero)
    if not match:
        return False
    sequencial, digito, ano, segmento, tribunal, origem = match.groups()
    base = int(f"{sequencial}{ano}{segmento}{tribunal}{origem}00")
    return f"{98 - (base % 97):02d}" == digito


def pagina_tem_cnj(texto: str) -> bool:
    return any(cnj_valido(m.group()) for m in CNJ_RE.finditer(texto))


def limpar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def extrair_sinais(texto: str) -> list[str]:
    dobrado = dobrar(texto)
    return [nome for nome, padrao in _SIGNALS if padrao.search(dobrado)]


def extrair_partes(texto: str) -> list[Parte]:
    partes: list[Parte] = []
    vistos: set[tuple[str, str]] = set()
    for match in PARTY_RE.finditer(texto):
        papel = _canon_papel(match.group("role"))
        nome = _limpar_nome(match.group("name"))
        if not papel or not nome:
            continue
        chave = (papel, dobrar(nome))
        if chave in vistos:
            continue
        vistos.add(chave)
        partes.append(Parte(papel=papel, nome=nome))
    return partes


def extrair_advogados(texto: str) -> list[Advogado]:
    achados: list[Advogado] = []
    ocupados: list[tuple[int, int]] = []
    for padrao in (_DIST_ADV_RE, _PROSE_ADV_RE):
        for match in padrao.finditer(texto):
            _guardar_advogado(
                achados,
                _limpar_nome(match.group("nome")),
                _oab(match.group("uf"), match.group("num")),
            )
            ocupados.append(match.span())
    for match in LAWYER_RE.finditer(texto):
        if _sobrepoe(match.span(), ocupados):
            continue
        corpo = match.group("body")
        oab_match = OAB_RE.search(corpo)
        nome = _limpar_nome(OAB_RE.sub("", corpo))
        oab = _formatar_oab(oab_match) if oab_match else ""
        if nome or oab:
            _guardar_advogado(achados, nome, oab)
    if not achados:
        for match in OAB_RE.finditer(texto):
            _guardar_advogado(achados, "", _formatar_oab(match))
        return achados
    faltantes = [adv for adv in achados if not adv.oab]
    if faltantes:
        livres = [_formatar_oab(match) for match in OAB_RE.finditer(texto)]
        usados = {adv.oab for adv in achados if adv.oab}
        fila = [oab for oab in livres if oab not in usados]
        for adv, oab in zip(faltantes, fila):
            adv.oab = oab
    return achados


def extrair_nomes_soltos(
    texto: str,
    partes: list[Parte],
    advogados: list[Advogado],
) -> list[str]:
    conhecidos = {dobrar(p.nome) for p in partes}
    conhecidos.update(dobrar(a.nome) for a in advogados if a.nome)
    nomes: list[str] = []
    for pedaco in _preambulo(texto):
        pedaco = CNJ_RE.sub("", pedaco)
        pedaco = re.sub(r"(?i)^processo\s*", "", pedaco).strip(" .;-")
        if not pedaco or _eh_rotulo(pedaco):
            continue
        if not _parece_nome(pedaco):
            continue
        chave = dobrar(pedaco)
        if chave in conhecidos:
            continue
        conhecidos.add(chave)
        nomes.append(pedaco)
    return nomes


def iter_pdf_pages(path: Path) -> Iterator[tuple[int, str]]:
    import pymupdf

    doc = pymupdf.open(path)
    try:
        for indice, page in enumerate(doc, start=1):
            yield indice, page.get_text("text", sort=True)
    finally:
        doc.close()


def iter_publicacoes(
    pages: Iterator[tuple[int, str]] | list[tuple[int, str]],
    *,
    data: str,
    caderno: str,
) -> Iterator[Publicacao]:
    vara_atual: str | None = None
    vara_proxima: str | None = None
    linhas: list[str] = []
    pagina: int | None = None
    cnj_aberto: str | None = None

    def fechar() -> Publicacao | None:
        nonlocal linhas, pagina
        if pagina is None or not linhas:
            linhas = []
            pagina = None
            return None
        bruto = "\n".join(linhas).strip()
        numero_pagina = pagina
        linhas = []
        pagina = None
        match = next(
            (m.group() for m in CNJ_RE.finditer(bruto) if cnj_valido(m.group())),
            "",
        )
        if not match:
            return None
        return _montar(bruto, match, numero_pagina, vara_atual, data, caderno)

    for numero, bruto in pages:
        for crua in bruto.splitlines():
            linha = limpar(crua)
            if not linha or _rodape(linha):
                continue
            if _cabecalho_vara(linha):
                vara_proxima = linha
                continue
            novos = [
                match
                for match in CNJ_RE.finditer(linha)
                if cnj_valido(match.group()) and match.group() != cnj_aberto
            ]
            if not novos:
                if pagina is not None:
                    linhas.append(linha)
                continue
            inicio = novos[0].start()
            cabeca = linha[:inicio].strip(" -.;")
            rotulo_do_novo = bool(re.fullmatch(r"PROCESSO", cabeca, re.IGNORECASE))
            if cabeca and pagina is not None and not rotulo_do_novo:
                linhas.append(cabeca)
            publicacao = fechar()
            if publicacao:
                yield publicacao
            cnj_aberto = novos[0].group()
            pagina = numero
            if vara_proxima:
                vara_atual = vara_proxima
                vara_proxima = None
            if rotulo_do_novo:
                linhas.append(cabeca)
            linhas.append(linha[inicio:].strip())
    ultima = fechar()
    if ultima:
        yield ultima


def _montar(
    bruto: str,
    cnj: str,
    pagina: int,
    vara: str | None,
    data: str,
    caderno: str,
) -> Publicacao:
    partes = extrair_partes(bruto)
    advogados = extrair_advogados(bruto)
    vara_campo = _vara_do_texto(bruto)
    return Publicacao(
        data=data,
        caderno=caderno,
        pagina=pagina,
        cnj=cnj,
        vara=vara_campo or vara,
        texto=limpar(bruto),
        partes=partes,
        nomes=extrair_nomes_soltos(bruto, partes, advogados),
        advogados=advogados,
        sinais=extrair_sinais(bruto),
    )


def _canon_papel(rotulo: str) -> str:
    for padrao, canon in _ROLE_CANON:
        if padrao.match(rotulo.strip()):
            return canon
    return ""


def _limpar_nome(nome: str) -> str:
    nome = OAB_RE.sub("", nome)
    nome = limpar(nome).strip(" -.;,")
    nome = re.sub(r"(?i)\s+e\s+outros?$", "", nome).strip()
    if len(nome) < 2 or nome.endswith(":"):
        return ""
    return nome


def _vara_do_texto(texto: str) -> str | None:
    aceitas = [
        vara
        for match in _VARA_RE.finditer(texto)
        if (vara := limpar(match.group("vara"))) and _vara_aceitavel(vara)
    ]
    return aceitas[-1] if aceitas else None


def _vara_aceitavel(linha: str) -> bool:
    if not 6 <= len(linha) <= 80 or not COURT_RE.search(linha):
        return False
    if re.search(r"rela[cç][aã]o\s+dos\s+feitos", linha, re.IGNORECASE):
        return False
    letras = [c for c in linha if c.isalpha()]
    if not letras:
        return False
    return sum(c.isupper() for c in letras) / len(letras) >= 0.6


def _oab(uf: str, numero: str) -> str:
    return f"{uf.upper()} {numero.replace('.', '')}".strip()


def _guardar_advogado(achados: list[Advogado], nome: str, oab: str) -> None:
    chave = (dobrar(nome), oab)
    if any((dobrar(adv.nome), adv.oab) == chave for adv in achados):
        return
    if nome or oab:
        achados.append(Advogado(nome=nome, oab=oab))


def _sobrepoe(trecho: tuple[int, int], ocupados: list[tuple[int, int]]) -> bool:
    inicio, fim = trecho
    return any(not (fim <= a or inicio >= b) for a, b in ocupados)


def _formatar_oab(match: re.Match[str] | None) -> str:
    if match is None:
        return ""
    uf = (match.group("uf") or "").upper()
    numero = match.group("num").replace(".", "")
    return f"{uf} {numero}".strip()


def _preambulo(texto: str) -> list[str]:
    corte = _PREAMBLE_END.search(texto)
    cabeca = texto[: corte.start()] if corte else texto[:800]
    return [p.strip(" .;") for p in re.split(r"\s+-\s+", cabeca) if p.strip()]


def _eh_rotulo(pedaco: str) -> bool:
    return bool(PARTY_RE.match(pedaco) or re.match(r"(?i)advogad", pedaco) or OAB_RE.fullmatch(pedaco.strip()))


def _parece_nome(pedaco: str) -> bool:
    if any(ch.isdigit() for ch in pedaco):
        return False
    if not 5 <= len(pedaco) <= 80 or CLASS_HINT.search(pedaco):
        return False
    if _COMPANY.search(pedaco):
        return True
    palavras = pedaco.replace(".", "").split()
    if not 2 <= len(palavras) <= 8:
        return False
    for palavra in palavras:
        if palavra.lower() in _PARTICLES:
            continue
        if not _WORD.fullmatch(palavra):
            return False
    return True


def _rodape(linha: str) -> bool:
    if linha.isdigit():
        return True
    if re.fullmatch(r"p[aá]gina\s+\d+", linha, re.IGNORECASE):
        return True
    return bool(FOOTER_RE.search(linha))


def _cabecalho_vara(linha: str) -> bool:
    if ":" in linha or CNJ_RE.search(linha):
        return False
    return _vara_aceitavel(linha)
