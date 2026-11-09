import pytest

from guicredito.djen.modelos import Bloco
from guicredito.djen.sinais import detectar_sinais

PADRAO_1 = (
    "Caso seja fornecido novo endereço para a citação, com a manifestação deverá ser providenciado o "
    "recolhimento das custas respectivas - salvo se a parte for beneficiária da justiça gratuita - e o "
    'peticionamento eletrônico deverá observar o evento/tipo de documento "Pedido de citação em novo endereço".'
)
PADRAO_2 = (
    "No silêncio , será aplicado o disposto no artigo 485, § 1º, do Código de Processo Civil ou os autos "
    "serão remetidos ao arquivo provisório, conforme o caso."
)
PADRAO_3 = (
    "Para viabilizar a realização da(s) pesquisa(s) eletrônica(s) requerida(s), deverá a parte interessada "
    "providenciar o(a): 1) recolhimento do valor ou, se o caso, a complementação correspondente à(s) pesquisa(s) "
    "eletrônica(s) pleiteada(s) ( Sisbajud, Renajud , Infojud , Serasajud , Comgasjud , Infoseg , Siel, CRCjud , "
    "Censec , SPCjud, ONR , Sniper, entre outras) , salvo se beneficiário da justiça gratuita , na quantia abaixo "
    "indicada ( com base na UFESP atualmente vigente ) , para cada pesquisa em cada pessoa/ CPF-CNPJ :"
)
PADRAO_4 = (
    "O bloqueio não incidirá sobre valores impenhoráveis referentes a salários ou subsídios, "
    "vencimentos, pensões e aposentadorias (art. 833 do Código de Processo Civil)."
)
PADRAO_5 = (
    "Sem prejuízo das determinações anteriores, autorizo, desde já, o acesso aos sistemas RENAJUD e "
    "INFOJUD, caso requerido e mediante o recolhimento das custas, exceto para os beneficiários da "
    "gratuidade da justiça, juntando-se as minutas aos autos."
)
PADRAO_6 = (
    "Ciência à parte interessada acerca da resposta da ordem pelo Sistema SisbaJud - Bloqueio negativo "
    "ou valores irrisórios desbloqueados - devendo a parte interessada requerer o que de direito, em "
    "5 (cinco) dias, sob pena de arquivamento do feito."
)
PADRAO_7 = (
    "Caso o executado não possua advogados constituídos, caberá ao exequente providenciar o "
    "recolhimento da taxa postal ou guia de condução do Oficial de Justiça para proceder a intimação "
    "pessoal do executado, acaso não seja beneficiário da justiça gratuita, no prazo de cinco dias, "
    "sob pena de arquivamento do feito e desbloqueio dos valores."
)
PADRAO_8 = (
    "INTIME-SE a parte executada, pelo DJE (na pessoa de seu advogado constituído nos autos) ou por "
    "carta, com aviso de recebimento (quando representado pela Defensoria Pública ou não tiver "
    "procurador constituído nos autos) ou por edital (se citado fictamente) para, no prazo de 05 "
    "(cinco) dias, questionar essa medida, ficando o executado advertido ainda que, não apresentada "
    "manifestação no prazo indicado, converter-se-á a indisponibilidade em penhora, sem necessidade de "
    "lavratura de termo, iniciando-se automaticamente, a partir do sexto (6º) dia, o prazo legal de "
    "15 (quinze) dias para apresentação de impugnação, independentemente de nova intimação."
)
PADRAO_9 = (
    "FULANO EXEMPLO: juntar aos autos o ofício com registro geral de indicação da defensoria "
    "OAB/SP para expedição da certidão de honorários."
)

D = Bloco.DESGASTE
P = Bloco.PATRIMONIO
V = Bloco.VULNERABILIDADE
X = Bloco.DESCONTO
A = Bloco.ALERTA

DETECTAR = [
    ("bloqueio_negativo", D, 10, "bloqueio infrutífero", "A pesquisa via SISBAJUD restou infrutífera."),
    ("bloqueio_negativo", D, 10, "bloqueio infrutífero", "O bloqueio de ativos financeiros resultou negativo."),
    ("acordo_frustrado", D, 10, "acordo frustrado", "A audiência de conciliação restou infrutífera."),
    ("acordo_frustrado", D, 10, "acordo frustrado", "Não houve acordo entre as partes."),
    ("arquivamento_provisorio", D, 8, "arquivamento provisório", "Remetam-se os autos ao arquivo provisório."),
    (
        "leilao_negativo",
        P,
        20,
        "leilão negativo",
        "O leilão do imóvel restou negativo, por ausência de licitantes.",
    ),
    (
        "imovel_penhorado",
        P,
        15,
        "imóvel penhorado/avaliado",
        "Lavre-se o termo de penhora do imóvel de matrícula nº 12.345.",
    ),
    ("imovel_penhorado", P, 15, "imóvel penhorado/avaliado", "Juntado o laudo de avaliação do imóvel."),
    ("bem_de_familia", P, 12, "bem de família", "Alega a executada tratar-se de bem de família."),
    ("penhora", P, 6, "penhora", "Defiro a penhora on-line."),
    ("veiculo", P, 4, "veículo", "Restrição via RENAJUD sobre o veículo."),
    (
        "superendividamento",
        V,
        15,
        "superendividamento",
        "Repactuação com base na Lei 14.181/2021 (superendividamento).",
    ),
    (
        "gratuidade_devedor",
        V,
        8,
        "justiça gratuita (devedor)",
        "Defiro ao executado os benefícios da justiça gratuita.",
    ),
    ("defensoria", V, 8, "Defensoria Pública", "O executado é assistido pela Defensoria Pública."),
    (
        "idoso",
        V,
        8,
        "idoso(a)",
        "Anote-se a prioridade de tramitação, por ser a executada pessoa idosa.",
    ),
    (
        "salario_impenhoravel",
        V,
        6,
        "salário/aposentadoria impenhorável",
        "Os valores bloqueados são proventos de aposentadoria, impenhoráveis nos termos do art. 833, IV, do CPC.",
    ),
    ("sem_bens", X, -10, "⚠ sem bens localizados", "Não foram localizados bens penhoráveis."),
    (
        "sem_bens",
        X,
        -10,
        "⚠ sem bens localizados",
        "Suspendo a execução nos termos do art. 921, III, do CPC.",
    ),
    (
        "prescricao_intercorrente",
        X,
        -10,
        "⚠ prescrição intercorrente",
        "Manifeste-se o exequente sobre a prescrição intercorrente.",
    ),
    (
        "devedor_nao_localizado",
        A,
        0,
        "⚠ devedor não localizado",
        "Juntada de Carta pelo Correio - devolvida sem cumprimento",
    ),
    (
        "devedor_nao_localizado",
        A,
        0,
        "⚠ devedor não localizado",
        "O executado não foi localizado no endereço indicado.",
    ),
    (
        "devedor_nao_localizado",
        A,
        0,
        "⚠ devedor não localizado",
        "Manifeste-se sobre a citação negativa.",
    ),
    ("leilao_negativo", P, 20, "leilão negativo", "O leilão restou deserto."),
    ("leilao_negativo", P, 20, "leilão negativo", "Declaro deserto o leilão."),
    ("leilao_negativo", P, 20, "leilão negativo", "A praça restou deserta."),
    ("leilao_negativo", P, 20, "leilão negativo", "A hasta restou negativa."),
    (
        "imovel_penhorado",
        P,
        15,
        "imóvel penhorado/avaliado",
        "Penhore-se o imóvel de matrícula nº 12.345.",
    ),
    (
        "arquivamento_provisorio",
        D,
        8,
        "arquivamento provisório",
        "Determino o arquivamento provisório dos autos.",
    ),
    (
        "arquivamento_provisorio",
        D,
        8,
        "arquivamento provisório",
        "Arquivem-se provisoriamente os autos.",
    ),
    (
        "bloqueio_negativo",
        D,
        10,
        "bloqueio infrutífero",
        "Certifico que a pesquisa pelo sistema Sisbajud retornou (negativo).",
    ),
    ("bloqueio_negativo", D, 10, "bloqueio infrutífero", "SISBAJUD: negativo."),
    ("bloqueio_negativo", D, 10, "bloqueio infrutífero", "A pesquisa via SISBAJUD restou negativa."),
    ("sem_bens", X, -10, "⚠ sem bens localizados", "Suspendo nos termos do artigo 921, III, do CPC."),
    ("sem_bens", X, -10, "⚠ sem bens localizados", "Ausência de bens penhoráveis."),
    ("sem_bens", X, -10, "⚠ sem bens localizados", "Cuida-se de execução frustrada."),
    ("acordo_frustrado", D, 10, "acordo frustrado", "O acordo restou infrutífero."),
]

NAO_DETECTAR = [
    ("bloqueio_negativo", "Defiro a pesquisa via Sisbajud."),
    ("acordo_frustrado", "Designo audiência de conciliação."),
    ("arquivamento_provisorio", PADRAO_2),
    ("leilao_negativo", "Nomeio leiloeiro oficial."),
    ("imovel_penhorado", "Indique o exequente bens à penhora."),
    ("veiculo", PADRAO_3),
    ("gratuidade_devedor", "Defiro ao exequente os benefícios da justiça gratuita."),
    ("gratuidade_devedor", PADRAO_1),
    ("salario_impenhoravel", "Comprove o executado a impenhorabilidade."),
    ("sem_bens", "Suspendo o processo por 30 dias."),
    ("gratuidade_devedor", "Indefiro ao executado os benefícios da justiça gratuita."),
]


@pytest.mark.parametrize(
    "frase",
    [
        " ".join([PADRAO_1, PADRAO_2, PADRAO_3]),
        PADRAO_4,
        PADRAO_5,
        PADRAO_6,
        PADRAO_7,
        PADRAO_8,
        PADRAO_9,
    ],
)
def test_texto_padrao_nao_gera_sinal(frase):
    assert detectar_sinais(frase) == ()


@pytest.mark.parametrize("chave,bloco,pontos,rotulo,frase", DETECTAR)
def test_sinal_detectado(chave, bloco, pontos, rotulo, frase):
    sinais = {s.chave: s for s in detectar_sinais(frase)}
    assert chave in sinais
    sinal = sinais[chave]
    assert sinal.bloco is bloco
    assert sinal.pontos == pontos
    assert sinal.rotulo == rotulo


@pytest.mark.parametrize("chave,frase", NAO_DETECTAR)
def test_sinal_nao_detectado(chave, frase):
    assert chave not in {s.chave for s in detectar_sinais(frase)}


def test_um_sinal_por_chave():
    texto = "Defiro a penhora on-line. Mantenho a penhora já realizada."
    penhoras = [s for s in detectar_sinais(texto) if s.chave == "penhora"]
    assert len(penhoras) == 1
    assert penhoras[0].trecho == "Defiro a penhora on-line."


def test_trecho_e_a_frase_original():
    frase = "Alega a executada tratar-se de bem de família."
    sinais = {s.chave: s for s in detectar_sinais(frase)}
    assert sinais["bem_de_familia"].trecho == frase


def test_texto_padrao_nao_apaga_penhora_na_mesma_frase():
    texto = "Defiro a penhora do imóvel, salvo se a parte for beneficiária da justiça gratuita."
    assert "imovel_penhorado" in {s.chave for s in detectar_sinais(texto)}


def test_silencio_sem_artigo_485_ainda_e_arquivamento():
    texto = "No silêncio, remetam-se os autos ao arquivo provisório."
    assert any(s.chave == "arquivamento_provisorio" for s in detectar_sinais(texto))
