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
    "s.a.",
    "s/a",
    "eireli",
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
    "cumprimento de sentenca",
    "monitoria",
)
_ROTULO = re.compile(
    r"\b(REQUERENTE|REQUERID[OA](?:\([A-Z]\))?|EXEQUENTE|EXECUTAD[OA](?:\([A-Z]\))?|AUTOR|RÉU|REU)\s*:"
)
_PARADA = re.compile(
    r"\b(?:[A-ZÁÉÍÓÚÂÊÔÃÕÇÀÜ][A-ZÁÉÍÓÚÂÊÔÃÕÇÀÜ0-9()/.ºª\-]*\s*:|"
    r"ATO ORDINATÓRIO|ATO ORDINATORIO|DESPACHO|DECISÃO|DECISAO|SENTENÇA|SENTENCA)"
)
_PALAVRA_CURTA = re.compile(r"\b(?:epp|mei|cia)\b")
_ME_NO_FIM = re.compile(r"(?:^|\s)me$")


def classe_de_cobranca(nome_classe: str) -> bool:
    nome = normalizar(nome_classe)
    if any(marca in nome for marca in _FORA):
        return False
    return any(marca in nome for marca in _DENTRO)


def _empresa_pelo_nome(nome: str) -> bool:
    if any(marca in nome for marca in (*_FUNDO, *_BANCO, *_EMPRESA)):
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
        pos = contexto.find(nome)
        if pos == -1:
            pos = contexto.casefold().find(nome.casefold())
        if pos != -1:
            depois = contexto[pos + len(nome) : pos + len(nome) + 80]
            if "cnpj" in depois.casefold():
                return True
    return _empresa_pelo_nome(normalizar(nome))


def _papel(rotulo: str) -> str:
    base = rotulo.split("(")[0]
    if base.startswith("EXECUTAD") or base.startswith("REQUERID") or base in {"RÉU", "REU"}:
        return "devedor"
    return "credor"


def partes_do_cabecalho(texto: str) -> tuple[list[str], list[str]]:
    credores: list[str] = []
    devedores: list[str] = []
    for achado in _ROTULO.finditer(texto):
        inicio = achado.end()
        parada = _PARADA.search(texto, inicio)
        fim = parada.start() if parada else len(texto)
        nome = " ".join(texto[inicio:fim].split())
        if not nome:
            continue
        if _papel(achado.group(1)) == "devedor":
            devedores.append(nome)
        else:
            credores.append(nome)
    return credores, devedores
