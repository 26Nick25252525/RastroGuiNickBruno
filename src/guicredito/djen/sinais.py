import re

from guicredito.djen.modelos import Bloco, Sinal
from guicredito.djen.texto import frases, normalizar

PADROES: list[re.Pattern[str]] = [
    re.compile(r"salvo se (a parte for )?beneficiari.*justica gratuita"),
    re.compile(r"no silencio.*arquivo provisorio"),
    re.compile(r"para viabilizar a realizacao da\(s\) pesquisa"),
    re.compile(r"bloqueio nao incidira sobre valores impenhoraveis"),
    re.compile(r"autorizo, desde ja, o acesso aos sistemas renajud"),
    re.compile(r"ciencia a parte interessada acerca da resposta da ordem pelo sistema sisbajud"),
    re.compile(r"acaso nao seja beneficiario da justica gratuita"),
    re.compile(r"quando representado pela defensoria publica ou nao tiver procurador"),
    re.compile(r"registro geral de indicacao da defensoria"),
]

CATALOGO: list[tuple[str, Bloco, int, str, re.Pattern[str]]] = [
    (
        "bloqueio_negativo",
        Bloco.DESGASTE,
        10,
        "bloqueio infrutífero",
        re.compile(r"sisbajud.{0,50}infrutif|bloqueio.{0,80}(negativ|infrutif)"),
    ),
    (
        "acordo_frustrado",
        Bloco.DESGASTE,
        10,
        "acordo frustrado",
        re.compile(r"conciliacao.{0,40}infrutif|nao houve acordo"),
    ),
    (
        "arquivamento_provisorio",
        Bloco.DESGASTE,
        8,
        "arquivamento provisório",
        re.compile(r"arquivo provisorio"),
    ),
    (
        "leilao_negativo",
        Bloco.PATRIMONIO,
        20,
        "leilão negativo",
        re.compile(r"\bleilao\b.{0,80}negativ"),
    ),
    (
        "imovel_penhorado",
        Bloco.PATRIMONIO,
        15,
        "imóvel penhorado/avaliado",
        re.compile(r"penhora do imovel|avaliacao do imovel"),
    ),
    (
        "bem_de_familia",
        Bloco.PATRIMONIO,
        12,
        "bem de família",
        re.compile(r"bem de familia"),
    ),
    (
        "penhora",
        Bloco.PATRIMONIO,
        6,
        "penhora",
        re.compile(r"\bpenhora\b"),
    ),
    (
        "veiculo",
        Bloco.PATRIMONIO,
        4,
        "veículo",
        re.compile(r"\brenajud\b|\bveiculo\b"),
    ),
    (
        "superendividamento",
        Bloco.VULNERABILIDADE,
        15,
        "superendividamento",
        re.compile(r"superendividamento"),
    ),
    (
        "gratuidade_devedor",
        Bloco.VULNERABILIDADE,
        8,
        "justiça gratuita (devedor)",
        re.compile(r"(executad[oa]|devedor).{0,80}justica gratuita"),
    ),
    (
        "defensoria",
        Bloco.VULNERABILIDADE,
        8,
        "Defensoria Pública",
        re.compile(r"defensoria"),
    ),
    (
        "idoso",
        Bloco.VULNERABILIDADE,
        8,
        "idoso(a)",
        re.compile(r"\bidos[oa]\b"),
    ),
    (
        "salario_impenhoravel",
        Bloco.VULNERABILIDADE,
        6,
        "salário/aposentadoria impenhorável",
        re.compile(
            r"(salario|aposentadoria|proventos).{0,60}impenhor"
            r"|impenhor.{0,60}(salario|aposentadoria|proventos)"
        ),
    ),
    (
        "sem_bens",
        Bloco.DESCONTO,
        -10,
        "⚠ sem bens localizados",
        re.compile(r"nao foram localizados bens|art\.?\s*921"),
    ),
    (
        "prescricao_intercorrente",
        Bloco.DESCONTO,
        -10,
        "⚠ prescrição intercorrente",
        re.compile(r"prescricao intercorrente"),
    ),
    (
        "devedor_nao_localizado",
        Bloco.ALERTA,
        0,
        "⚠ devedor não localizado",
        re.compile(r"devolvida sem cumprimento|nao foi localizado|citacao negativa"),
    ),
]


def eh_texto_padrao(frase_normalizada: str) -> bool:
    return any(padrao.search(frase_normalizada) for padrao in PADROES)


def detectar_sinais(texto: str) -> tuple[Sinal, ...]:
    vistos: set[str] = set()
    achados: list[Sinal] = []
    for frase in frases(texto):
        norm = normalizar(frase)
        if eh_texto_padrao(norm):
            continue
        for chave, bloco, pontos, rotulo, regex in CATALOGO:
            if chave in vistos or not regex.search(norm):
                continue
            vistos.add(chave)
            achados.append(Sinal(chave, bloco, pontos, rotulo, frase[:300]))
    return tuple(achados)
