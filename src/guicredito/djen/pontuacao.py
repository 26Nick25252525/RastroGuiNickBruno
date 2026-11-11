"""Turn one case into a score, then rank the list.

``pipeline`` calls ``pontuar`` on each case that still has a natural-person
debtor, passing the current year. Points come from the creditor type set
by ``partes``, the debt age on the ``Caso`` built by ``casos``, and the
``Sinal`` list from ``sinais``. Wear, assets and vulnerability each stop
at a cap. Discounts do not. A missing debtor subtracts 15 more. The total
never goes below 0.

``ordenar`` sorts by total (highest first), then by older debt, then by
process number, and cuts the list at ``limite``. ``planilha`` writes that
cut, in that order, as the Casos sheet.
"""

from collections.abc import Iterable

from guicredito.djen.modelos import Bloco, Caso, CasoPontuado, Pontuacao, TipoCredor

PONTOS_CREDOR = {
    TipoCredor.BANCO: 20,
    TipoCredor.FUNDO: 12,
    TipoCredor.PESSOA: 8,
    TipoCredor.EMPRESA: 5,
}
TETO_BLOCO = {
    Bloco.DESGASTE: 25,
    Bloco.PATRIMONIO: 20,
    Bloco.VULNERABILIDADE: 15,
}
DESCONTO_SEM_DEVEDOR = 15


def _pontos_idade(anos: int) -> int:
    if anos >= 10:
        return 20
    if anos >= 6:
        return 15
    if anos >= 3:
        return 8
    return 0


def _soma_bloco(caso: Caso, bloco: Bloco) -> int:
    soma = sum(sinal.pontos for sinal in caso.sinais if sinal.bloco is bloco)
    teto = TETO_BLOCO.get(bloco)
    if teto is None:
        return soma
    return min(soma, teto)


def pontuar(caso: Caso, ano_atual: int) -> Pontuacao:
    credor = PONTOS_CREDOR.get(caso.tipo_credor, 0) if caso.tipo_credor is not None else 0
    idade = _pontos_idade(ano_atual - caso.ano_divida)
    desgaste = _soma_bloco(caso, Bloco.DESGASTE)
    patrimonio = _soma_bloco(caso, Bloco.PATRIMONIO)
    vulnerabilidade = _soma_bloco(caso, Bloco.VULNERABILIDADE)
    descontos = _soma_bloco(caso, Bloco.DESCONTO)
    if caso.devedor is None:
        descontos -= DESCONTO_SEM_DEVEDOR
    total = max(0, credor + idade + desgaste + patrimonio + vulnerabilidade + descontos)
    return Pontuacao(credor, idade, desgaste, patrimonio, vulnerabilidade, descontos, total)


def ordenar(casos: Iterable[CasoPontuado], limite: int) -> list[CasoPontuado]:
    return sorted(
        casos,
        key=lambda item: (-item.pontos.total, item.caso.ano_divida, item.caso.numero_processo),
    )[:limite]
