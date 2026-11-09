import html
import re
import unicodedata

_CSS_SOLTO = re.compile(
    r"(?:body|#[A-Za-z0-9_-]+)\s*\{[^}]*\}\s*;?",
    re.IGNORECASE,
)
_STYLE = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_ESPACOS = re.compile(r"\s+")
_QUEBRA = re.compile(r"[.!;?] ")
_CONTROLE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def limpar_html(html_texto: str | None) -> str:
    if not html_texto:
        return ""
    sem_style = _STYLE.sub(" ", html_texto)
    sem_css = _CSS_SOLTO.sub(" ", sem_style)
    sem_tags = _TAG.sub(" ", sem_css)
    texto = html.unescape(sem_tags)
    return _ESPACOS.sub(" ", texto).strip()


def normalizar(s: str) -> str:
    sem_acento = unicodedata.normalize("NFD", s)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return _ESPACOS.sub(" ", sem_acento).strip().lower()


def frases(texto: str) -> list[str]:
    partes: list[str] = []
    inicio = 0
    for marca in _QUEBRA.finditer(texto):
        depois = marca.end()
        if depois < len(texto) and texto[depois].isupper():
            partes.append(texto[inicio : marca.start() + 1].strip())
            inicio = depois
    resto = texto[inicio:].strip()
    if resto:
        partes.append(resto)
    return partes


def _digitos_cnj(numero: str) -> str:
    return re.sub(r"\D", "", numero)


def formatar_cnj(numero: str) -> str:
    digitos = _digitos_cnj(numero)
    if len(digitos) != 20:
        return numero
    return (
        f"{digitos[0:7]}-{digitos[7:9]}.{digitos[9:13]}."
        f"{digitos[13]}.{digitos[14:16]}.{digitos[16:20]}"
    )


def ano_cnj(numero: str) -> int | None:
    digitos = _digitos_cnj(numero)
    if len(digitos) != 20:
        return None
    return int(digitos[9:13])


def limpar_para_excel(s: str) -> str:
    return _CONTROLE.sub("", s)
