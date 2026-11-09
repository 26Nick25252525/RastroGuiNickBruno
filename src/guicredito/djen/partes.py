import re

from guicredito.djen.modelos import TipoCredor
from guicredito.djen.texto import normalizar

_BANCO = (
    "banco",
    "caixa economica",
    "cooperativa de credito",
    "sicoob",
    "sicredi",
    "financeira",
    "credito, financiamento e investimento",
)
_FUNDO = (
    "fidc",
    "fundo de investimento",
    "direitos creditorios",
    "securitizadora",
)
_EMPRESA = (
    "ltda",
    "s.a",
    "s/a",
    "eireli",
    "limitada",
    "sociedade anonima",
    "companhia",
    "condominio",
    "associacao",
)
_FORA = (
    "fazenda publica",
    "alimentos",
    "acoes coletivas",
    "execucao fiscal",
    "execucao da pena",
    "penal",
    "busca e apreensao",
    "despejo",
    "procedimento comum",
    "embargos",
)
_DENTRO = (
    "execucao de titulo extrajudicial",
    "monitoria",
)
_CUMPRIMENTO = re.compile(r"cumprimento(?: provisorio)? de (?:sentenca|decisao)")
_ROTULO = re.compile(
    r"\b(REQUERENTES|REQUERENTE|REQUERIDOS|REQUERIDAS|REQUERID[OA](?:\([A-Z]\))?|"
    r"EXEQUENTES|EXEQUENTE|EXECUTADOS|EXECUTADAS|EXECUTAD[OA](?:\([A-Z]\))?|"
    r"AUTORES|AUTOR|RÉUS|REUS|RÉU|REU)\s*:"
)
_PARADA = re.compile(
    r"\b(?!CPF\s*:)(?!CNPJ\s*:)"
    r"(?:[A-ZÁÉÍÓÚÂÊÔÃÕÇÀÜ][A-ZÁÉÍÓÚÂÊÔÃÕÇÀÜ0-9()/.ºª\-]*\s*:|"
    r"ATO ORDINATÓRIO|ATO ORDINATORIO|DESPACHO|DECISÃO|DECISAO|SENTENÇA|SENTENCA)"
)
_DOC_NUMERO = re.compile(r",?\s*\b(?:CNPJ|CPF)\b\s*:?\s*[\d./\-]+", re.IGNORECASE)
_MARCA_NO_MEIO = re.compile(r"\b(?:ltda|s\.a|s/a|eireli|limitada|companhia)\b", re.IGNORECASE)
_PALAVRA_CURTA = re.compile(r"\b(?:epp|mei|cia)\b")
_ME_NO_FIM = re.compile(r"(?:^|\s)me$")


def classe_de_cobranca(nome_classe: str) -> bool:
    nome = normalizar(nome_classe)
    if any(marca in nome for marca in _FORA):
        return False
    if _CUMPRIMENTO.search(nome):
        return True
    return any(marca in nome for marca in _DENTRO)


def _empresa_pelo_nome(nome: str) -> bool:
    if any(marca in nome for marca in (*_FUNDO, *_BANCO, *_EMPRESA)):
        return True
    if re.search(r"\bsa\b", nome):
        return True
    return _ME_NO_FIM.search(nome) is not None or _PALAVRA_CURTA.search(nome) is not None


def tipo_credor(nome: str) -> TipoCredor:
    normal = normalizar(nome)
    if any(marca in normal for marca in _FUNDO):
        return TipoCredor.FUNDO
    if any(marca in normal for marca in _BANCO):
        return TipoCredor.BANCO
    if _empresa_pelo_nome(normal):
        return TipoCredor.EMPRESA
    return TipoCredor.PESSOA


def eh_empresa(nome: str, contexto: str = "") -> bool:
    if contexto and nome:
        achados = re.compile(rf"(?<!\w){re.escape(nome)}(?!\w)", re.IGNORECASE).finditer(contexto)
        for achado in achados:
            janela = contexto[achado.end() : achado.end() + 80]
            rotulo = _ROTULO.search(janela)
            if rotulo:
                janela = janela[: rotulo.start()]
            cpf = re.search(r"\bcpf\b", janela, re.IGNORECASE)
            cnpj = re.search(r"\bcnpj\b", janela, re.IGNORECASE)
            if cpf and (cnpj is None or cpf.start() < cnpj.start()):
                return False
            if cnpj and not _MARCA_NO_MEIO.search(janela[: cnpj.start()]):
                return True
    return _empresa_pelo_nome(normalizar(nome))


def _papel(rotulo: str) -> str:
    base = rotulo.split("(")[0]
    if base.startswith("EXECUTAD") or base.startswith("REQUERID") or base in {"RÉU", "REU", "RÉUS", "REUS"}:
        return "devedor"
    return "credor"


def _limpar_nomes(bruto: str) -> list[str]:
    tinha_documento = _DOC_NUMERO.search(bruto) is not None
    sem_doc = " ".join(_DOC_NUMERO.sub(" ", bruto).split()).strip(" ,")
    if not sem_doc:
        return []
    if not tinha_documento:
        return [sem_doc]
    return [
        parte.strip(" ,")
        for parte in re.split(r"\s+\be\b\s+", sem_doc, flags=re.IGNORECASE)
        if parte.strip(" ,")
    ]


def partes_do_cabecalho(texto: str) -> tuple[list[str], list[str]]:
    credores: list[str] = []
    devedores: list[str] = []
    for achado in _ROTULO.finditer(texto):
        inicio = achado.end()
        parada = _PARADA.search(texto, inicio)
        fim = parada.start() if parada else len(texto)
        for nome in _limpar_nomes(texto[inicio:fim]):
            if _papel(achado.group(1)) == "devedor":
                devedores.append(nome)
            else:
                credores.append(nome)
    return credores, devedores
