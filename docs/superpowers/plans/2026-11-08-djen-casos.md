# Achador de casos de dívida no DJEN: plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA: use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans para implementar este plano tarefa por tarefa. Os passos usam checkbox (`- [ ]`) para acompanhamento.
> **No Cursor, sem essas skills:** siga as tarefas na ordem. Em cada passo, rode o comando indicado e confira a saída esperada antes de marcar o checkbox.

**Objetivo:** criar um comando que baixa os cadernos do TJSP no DJEN de um período, separa as cobranças travadas contra pessoas físicas, dá pontos a cada caso e gera uma planilha Excel com 3 abas.

**Arquitetura:** pacote Python `guicredito.djen` com um módulo por responsabilidade. A leitura passa duas vezes pelos ZIPs:
1. A primeira passada guarda só um resumo de cada publicação de cobrança (partes, sinais, anos citados), sem o texto.
2. Com esse resumo, monta os casos, pontua e escolhe os 300 melhores.
3. A segunda passada busca os textos completos só desses processos, para a aba "Publicações".

Assim, ~1 milhão de publicações não ficam todas na memória ao mesmo tempo.

**Tecnologia:** Python ≥ 3.12, `urllib` (biblioteca padrão) para HTTP, `openpyxl` para o Excel, `pytest` para os testes.

**Spec:** `docs/superpowers/specs/2026-11-08-djen-casos-design.md`. Leia a spec inteira antes da Tarefa 1. Este plano decide o *como*; o *porquê* está lá.

## Restrições globais

- Python `>=3.12`, com ambiente virtual em `.venv/` (já ignorado pelo git).
- Dependências: `openpyxl>=3.1` (execução) e `pytest>=8` (desenvolvimento). Nenhuma outra.
- TDD: o teste vem antes do código em toda tarefa.
- Branch `feature/djen-casos`. Nunca commitar na `main`. Commits no padrão convencional (`feat:`, `fix:`, `chore:`, `test:`, `docs:`), com verbo no presente.
- **Dados pessoais:**
  - `dados/` e `saida/` nunca vão para o git.
  - Os testes usam só nomes fictícios ("JOÃO EXEMPLO", "BANCO EXEMPLO S.A.") e nenhum CPF/CNPJ real.
- **Rede:**
  - Os testes nunca acessam a rede.
  - O programa só acessa `https://comunicaapi.pje.jus.br/api/v1/caderno/{SIGLA}/{AAAA-MM-DD}/D` e a URL do ZIP que essa chamada devolve.
- Tribunal padrão `TJSP`. Período padrão: os **5 últimos dias úteis até ontem**. Limite padrão da aba Casos: **300**.
- Arquivo de saída: `saida/casos_djen_{inicio}_a_{fim}.xlsx`, com datas `AAAA-MM-DD`.
- **Não mudar pesos, cortes ou classes sem o Nick.** Os valores da spec, seções 8 e 9, estão copiados nas Tarefas 4, 5 e 7.

## Pontos de atenção na revisão

1. **Caracteres de controle no texto** (`\x00`–`\x08`, `\x0b`, `\x0c`, `\x0e`–`\x1f`): o `openpyxl` lança `IllegalCharacterError` e a planilha não é salva. Esses caracteres precisam ser removidos antes de gravar. Testado nas Tarefas 1 e 8.
2. **Dia sem caderno** (fim de semana, feriado sem publicação, dia ainda não gerado: HTTP 404): o programa pula o dia, avisa no terminal e lista o dia na aba "Como ler". Não pode quebrar. Testado nas Tarefas 3 e 9.
3. **Link do ZIP expirado (300 s) ou erro 403/429/5xx no meio do download:** o programa pede os metadados de novo e repete até 3 vezes. Nunca deixa ZIP parcial no cache. Testado na Tarefa 3.
4. **Publicação cancelada** (`ativo` falso ou `data_cancelamento` preenchida): é ignorada. Testado na Tarefa 2.
5. **Rodar de novo o mesmo período:** usa o cache, sem baixar ~700 MB de novo. Se o caderno foi republicado (`versao` 2), baixa a versão nova. Testado na Tarefa 3.

---

## Estrutura de arquivos

```
pyproject.toml
src/guicredito/__init__.py
src/guicredito/djen/__init__.py
src/guicredito/djen/__main__.py   linha de comando
src/guicredito/djen/modelos.py    dataclasses e enums compartilhados
src/guicredito/djen/texto.py      limpar HTML, normalizar, frases, número CNJ, limpar para Excel
src/guicredito/djen/fonte.py      cliente HTTP, dias úteis, metadados, download com cache
src/guicredito/djen/leitura.py    ZIP do caderno → Publicacao
src/guicredito/djen/partes.py     classe de cobrança, tipo de credor, empresa ou pessoa, cabeçalho
src/guicredito/djen/sinais.py     catálogo de sinais, textos-padrão, detecção
src/guicredito/djen/casos.py      resumir publicação, montar casos, ano da dívida, comarca
src/guicredito/djen/pontuacao.py  pontuar e ordenar
src/guicredito/djen/planilha.py   gravar o .xlsx
src/guicredito/djen/pipeline.py   orquestrar uma rodada
tests/djen/conftest.py            fábrica de item/ZIP sintético e cliente HTTP falso
tests/djen/test_<módulo>.py       um arquivo de teste por módulo
```

---

### Tarefa 1: Base do projeto, modelos e utilitários de texto

**Arquivos:**
- Criar: `pyproject.toml`, `src/guicredito/__init__.py`, `src/guicredito/djen/__init__.py`, `src/guicredito/djen/modelos.py`, `src/guicredito/djen/texto.py`
- Teste: `tests/djen/test_texto.py`

**Interfaces:**
- Consome: nada.
- Produz, em `modelos.py` (todos `@dataclass(frozen=True)`, exceto `ResumoRodada`):

```python
class TipoCredor(StrEnum):
    BANCO = "Banco"; FUNDO = "Fundo"; PESSOA = "Pessoa"; EMPRESA = "Empresa"

class Bloco(StrEnum):
    DESGASTE = "desgaste"; PATRIMONIO = "patrimonio"; VULNERABILIDADE = "vulnerabilidade"
    DESCONTO = "desconto"; ALERTA = "alerta"

Destinatario(nome: str, polo: str)                      # polo "A" | "P" | outro
Publicacao(id: int, data: date, tipo: str, orgao: str, numero_processo: str, classe: str,
           texto: str, link: str, destinatarios: tuple[Destinatario, ...])   # texto já limpo
CadernoInfo(sigla: str, data: date, versao: int, total_comunicacoes: int,
            numero_paginas: int, tamanho_bytes: int, hash: str, url: str)
Sinal(chave: str, bloco: Bloco, pontos: int, rotulo: str, trecho: str)
Parte(nome: str, empresa: bool)
ResumoPublicacao(numero_processo: str, data: date, tipo: str, orgao: str, classe: str, link: str,
                 credores: tuple[str, ...], devedores: tuple[Parte, ...],
                 sinais: tuple[Sinal, ...], anos_citados: tuple[int, ...])
Caso(numero_processo: str, classe: str, orgao: str, comarca: str, link: str,
     credor: str | None, tipo_credor: TipoCredor | None,
     devedor: str | None, avalista: bool, so_empresa: bool,
     ano_divida: int, sinais: tuple[Sinal, ...],
     ultima_data: date, ultimo_tipo: str, n_publicacoes: int)
Pontuacao(credor: int, idade: int, desgaste: int, patrimonio: int,
          vulnerabilidade: int, descontos: int, total: int)
CasoPontuado(caso: Caso, pontos: Pontuacao)
@dataclass
ResumoRodada(inicio: date, fim: date, cadernos: list[CadernoInfo], dias_sem_caderno: list[date],
             publicacoes_lidas: int, publicacoes_cobranca: int, processos: int,
             processos_so_empresa: int, casos_na_planilha: int, gerado_em: datetime)
```

- Produz, em `texto.py`:
  - `limpar_html(html: str | None) -> str`
  - `normalizar(s: str) -> str`
  - `frases(texto: str) -> list[str]`
  - `formatar_cnj(numero: str) -> str`
  - `ano_cnj(numero: str) -> int | None`
  - `limpar_para_excel(s: str) -> str`

- [ ] **Passo 1: Criar `pyproject.toml` e o ambiente**

O `pyproject.toml` deve ter: `[project]` com `name = "guicredito"`, `version = "0.1.0"`, `requires-python = ">=3.12"` e `dependencies = ["openpyxl>=3.1"]`; `[project.optional-dependencies] dev = ["pytest>=8"]`; build com setuptools e pacotes em `src/`; `[tool.pytest.ini_options] testpaths = ["tests"]`.

Rodar: `python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`
Esperado: termina sem erro, e `python -c "import openpyxl, pytest"` não imprime nada.

- [ ] **Passo 2: Escrever os testes que falham em `tests/djen/test_texto.py`**

```python
CSS = ("body{ padding: 10px; font-family: Times New Roman; font-size:13pt }; "
       "#divHeader{ line-height:25px; margin-bottom:30px }; #divBody{ max-width:90%; text-align:justify } ")

def test_limpar_html_remove_css_solto_tags_e_entidades():
    html = (f"<html><head><style>x{{}}</style></head><body>{CSS}<section><b>EXECU&Ccedil;&Atilde;O "
            "DE T&Iacute;TULO</b></section><p>Intima&ccedil;&atilde;o   realizada.</p></body></html>")
    assert limpar_html(html) == "EXECUÇÃO DE TÍTULO Intimação realizada."

def test_limpar_html_aceita_none_e_vazio():
    assert limpar_html(None) == "" and limpar_html("") == ""

def test_normalizar():
    assert normalizar("  Execução   de TÍTULO ") == "execucao de titulo"

def test_frases_nao_quebra_em_abreviacao_nem_numero():
    t = "Vistos. Suspendo nos termos do art. 921, III, do CPC. Conforme autos de n. 1030830-98.2015.8.26.0100, intime-se."
    assert frases(t) == ["Vistos.", "Suspendo nos termos do art. 921, III, do CPC.",
                         "Conforme autos de n. 1030830-98.2015.8.26.0100, intime-se."]

def test_formatar_cnj_e_ano():
    assert formatar_cnj("10034641820228260269") == "1003464-18.2022.8.26.0269"
    assert ano_cnj("10034641820228260269") == 2022
    assert ano_cnj("123") is None

def test_limpar_para_excel_remove_caracteres_de_controle():
    assert limpar_para_excel("a\x00b\x0bc\x1fd\te\nf") == "abcd\te\nf"
```

- [ ] **Passo 3: Rodar e ver falhar**

Rodar: `pytest tests/djen/test_texto.py -v`
Esperado: FAIL (ImportError).

- [ ] **Passo 4: Implementar `modelos.py` e as funções de `texto.py`**

- `frases`: quebra depois de `.`, `;`, `!` ou `?` **somente** quando vem espaço seguido de letra maiúscula (incluindo acentuadas). Assim "art. 921" e "n. 1030830" ficam inteiros.
- `limpar_html`: tira `<style>…</style>`, as regras CSS soltas do início (`body{…}`, `#divX{…}`), as tags e as entidades HTML (`html.unescape`), e junta espaços repetidos.

- [ ] **Passo 5: Rodar e ver passar**

Rodar: `pytest tests/djen/test_texto.py -v`
Esperado: 6 passed.

- [ ] **Passo 6: Commit**

```bash
git add pyproject.toml src tests
git commit -m "feat: add project base, shared models and text helpers"
```

---

### Tarefa 2: Ler o ZIP do caderno

**Arquivos:**
- Criar: `src/guicredito/djen/leitura.py`, `tests/djen/conftest.py`
- Teste: `tests/djen/test_leitura.py`

**Interfaces:**
- Consome: `Publicacao` e `Destinatario` (Tarefa 1); `limpar_html` (Tarefa 1).
- Produz:
  - `ler_caderno(caminho_zip: Path) -> Iterator[Publicacao]`.
  - Em `conftest.py`, as fixtures `item(**alteracoes) -> dict` e `fazer_zip(pasta: Path, nome_base: str, arquivos: list[list[dict]]) -> Path`.
    - `fazer_zip` grava um JSON `{nome_base}_{k}.json` por lista, no formato `{"count": n, "items": [...]}`, como no caderno real (spec, seção 7.1).
    - Valores padrão de `item()`: `id=1`, `data_disponibilizacao="2026-11-06"`, `tipoComunicacao="Intimação"`, `nomeOrgao="UPJ da 1ª a 4ª Varas Civeis da Comarca de Itapetininga"`, `texto="<p>Texto.</p>"`, `numero_processo="10034641820228260269"`, `link="https://eproc1g.tjsp.jus.br/doc?x=1"`, `nomeClasse="EXECUçãO DE TíTULO EXTRAJUDICIAL"`, `ativo=True`, `data_cancelamento=None`, `destinatarios=[{"nome": "BANCO EXEMPLO S.A.", "polo": "A"}]`.

- [ ] **Passo 1: Escrever os testes que falham**

```python
def test_le_todos_os_arquivos_e_mapeia_campos(tmp_path, item, fazer_zip):
    z = fazer_zip(tmp_path, "TJSP-D-2026-11-06", [[item(id=1), item(id=2)], [item(id=3, texto="<b>Olá</b>")]])
    pubs = list(ler_caderno(z))
    assert [p.id for p in pubs] == [1, 2, 3]
    p = pubs[2]
    assert p.data == date(2026, 11, 6) and p.texto == "Olá" and p.numero_processo == "10034641820228260269"
    assert p.destinatarios == (Destinatario("BANCO EXEMPLO S.A.", "A"),)

def test_ignora_publicacao_cancelada(tmp_path, item, fazer_zip):
    z = fazer_zip(tmp_path, "c", [[item(id=1, ativo=False), item(id=2, data_cancelamento="2026-11-06"), item(id=3)]])
    assert [p.id for p in ler_caderno(z)] == [3]

def test_campos_ausentes_viram_vazios(tmp_path, item, fazer_zip):
    i = item(id=1, texto=None); del i["destinatarios"]
    p = next(ler_caderno(fazer_zip(tmp_path, "c", [[i]])))
    assert p.texto == "" and p.destinatarios == ()
```

- [ ] **Passo 2: Rodar e ver falhar**

Rodar: `pytest tests/djen/test_leitura.py -v`
Esperado: FAIL.

- [ ] **Passo 3: Implementar `ler_caderno`**

Abre o ZIP com `zipfile` e lê um JSON por vez (cada um tem ~4 MB), sem extrair para o disco.

- [ ] **Passo 4: Rodar e ver passar**

Rodar: `pytest tests/djen -v`
Esperado: todos passam.

- [ ] **Passo 5: Commit**

```bash
git add src tests
git commit -m "feat: read DJEN caderno zip into publications"
```

---

### Tarefa 3: Baixar cadernos com cache

**Arquivos:**
- Criar: `src/guicredito/djen/fonte.py`
- Modificar: `tests/djen/conftest.py` (adicionar o `ClienteFalso`)
- Teste: `tests/djen/test_fonte.py`

**Interfaces:**
- Consome: `CadernoInfo` (Tarefa 1).
- Produz:
  - `class HttpErro(Exception)`, com o atributo `status: int`.
  - `class ErroDownload(Exception)`.
  - `class ClienteHttp(Protocol)`, com dois métodos:
    - `get_json(url: str) -> dict`
    - `baixar(url: str, destino: Path) -> None`

    Os dois lançam `HttpErro` quando o status é diferente de 2xx.
  - `class ClienteUrllib`, a implementação real:
    - timeout de 60 s e `User-Agent: GUICredito/0.1`;
    - `baixar` grava em streaming, em blocos de 1 MB.
  - `URL_CADERNO = "https://comunicaapi.pje.jus.br/api/v1/caderno/{sigla}/{data}/D"`.
  - `dias_uteis(inicio: date, fim: date) -> list[date]`: de segunda a sexta, com as duas pontas incluídas. Feriados não são tratados aqui; dia sem caderno devolve 404.
  - `periodo_padrao(hoje: date) -> tuple[date, date]`: os 5 últimos dias úteis até ontem.
  - `buscar_metadados(cliente: ClienteHttp, sigla: str, dia: date) -> CadernoInfo | None`: devolve `None` quando a resposta é HTTP 404.
  - `baixar_caderno(cliente: ClienteHttp, sigla: str, dia: date, pasta: Path, espera: Callable[[float], None] = time.sleep) -> tuple[CadernoInfo, Path] | None`.
  - `ClienteFalso(metadados: dict[str, dict | None], arquivos: dict[str, bytes], falhas: dict[str, int] | None = None)`, em `conftest.py`:
    - guarda as chamadas feitas em `chamadas_get` e `chamadas_baixar`;
    - quando a URL não existe ou o valor é `None`, lança `HttpErro(404)`;
    - enquanto `falhas[url] > 0`, `baixar` diminui o contador e lança `HttpErro(403)`.

Fatos da API (spec, seção 7.1, verificados em 08/11/2026):
- o `hash` é o SHA-256 do ZIP;
- dia sem caderno devolve 404 com `{"erro": "Nenhum caderno encontrado para os parâmetros informados."}`;
- a `url` do ZIP expira em 300 s.

- [ ] **Passo 1: Escrever os testes que falham**

```python
def test_dias_uteis():
    assert dias_uteis(date(2026, 11, 2), date(2026, 11, 8)) == [date(2026, 11, d) for d in (2, 3, 4, 5, 6)]

def test_periodo_padrao():
    assert periodo_padrao(date(2026, 11, 8)) == (date(2026, 11, 2), date(2026, 11, 6))    # domingo
    assert periodo_padrao(date(2026, 11, 10)) == (date(2026, 11, 3), date(2026, 11, 9))   # terça

# helper: meta(conteudo: bytes, versao=1) -> dict no formato da spec 7.1, com hash=sha256(conteudo) e url="https://s3/z"

def test_sem_caderno_retorna_none(tmp_path):
    assert baixar_caderno(ClienteFalso({}, {}), "TJSP", date(2026, 11, 7), tmp_path) is None

def test_baixa_e_confere_hash(tmp_path):
    c = ClienteFalso({URL_06: meta(b"zip")}, {"https://s3/z": b"zip"})
    info, caminho = baixar_caderno(c, "TJSP", date(2026, 11, 6), tmp_path)
    assert caminho == tmp_path / "TJSP-D-2026-11-06_v1.zip" and caminho.read_bytes() == b"zip"

def test_usa_cache_na_segunda_vez(tmp_path):
    c = ClienteFalso({URL_06: meta(b"zip")}, {"https://s3/z": b"zip"})
    baixar_caderno(c, "TJSP", date(2026, 11, 6), tmp_path); baixar_caderno(c, "TJSP", date(2026, 11, 6), tmp_path)
    assert len(c.chamadas_baixar) == 1

def test_nova_versao_baixa_de_novo(tmp_path):
    (tmp_path / "TJSP-D-2026-11-06_v1.zip").write_bytes(b"velho")
    c = ClienteFalso({URL_06: meta(b"novo", versao=2)}, {"https://s3/z": b"novo"})
    _, caminho = baixar_caderno(c, "TJSP", date(2026, 11, 6), tmp_path)
    assert caminho.name == "TJSP-D-2026-11-06_v2.zip" and len(c.chamadas_baixar) == 1

def test_link_expirado_pede_metadados_de_novo(tmp_path):
    c = ClienteFalso({URL_06: meta(b"zip")}, {"https://s3/z": b"zip"}, falhas={"https://s3/z": 1})
    _, caminho = baixar_caderno(c, "TJSP", date(2026, 11, 6), tmp_path, espera=lambda s: None)
    assert caminho.exists() and len(c.chamadas_get) == 2 and not list(tmp_path.glob("*.part"))

def test_desiste_apos_3_falhas_sem_deixar_lixo(tmp_path):
    c = ClienteFalso({URL_06: meta(b"zip")}, {"https://s3/z": b"zip"}, falhas={"https://s3/z": 9})
    with pytest.raises(ErroDownload):
        baixar_caderno(c, "TJSP", date(2026, 11, 6), tmp_path, espera=lambda s: None)
    assert list(tmp_path.iterdir()) == []

def test_hash_diferente_conta_como_falha(tmp_path):
    c = ClienteFalso({URL_06: meta(b"zip")}, {"https://s3/z": b"corrompido"})
    with pytest.raises(ErroDownload):
        baixar_caderno(c, "TJSP", date(2026, 11, 6), tmp_path, espera=lambda s: None)
```

(`URL_06 = URL_CADERNO.format(sigla="TJSP", data="2026-11-06")`.)

- [ ] **Passo 2: Rodar e ver falhar**

Rodar: `pytest tests/djen/test_fonte.py -v`
Esperado: FAIL.

- [ ] **Passo 3: Implementar `fonte.py`**

Fluxo de `baixar_caderno`:
1. Pede os metadados. Se vier `None`, devolve `None`.
2. O destino é `{sigla}-D-{data}_v{versao}.zip`. Se o arquivo já existe e o SHA-256 bate com o `hash`, devolve sem baixar.
3. Baixa para `destino.zip.part`, confere o SHA-256 e renomeia para o destino final.
4. Se der `HttpErro` ou o hash não bater: apaga o `.part`, espera 2 s e depois 4 s, pede os metadados de novo (link novo) e tenta outra vez. São no máximo 3 tentativas; depois disso, lança `ErroDownload` com a data e o motivo.

- [ ] **Passo 4: Rodar e ver passar**

Rodar: `pytest tests/djen -v`
Esperado: todos passam.

- [ ] **Passo 5: Commit**

```bash
git add src tests
git commit -m "feat: download DJEN cadernos with hash-checked cache and retries"
```

---

### Tarefa 4: Classe de cobrança e partes

**Arquivos:**
- Criar: `src/guicredito/djen/partes.py`
- Teste: `tests/djen/test_partes.py`

**Interfaces:**
- Consome: `TipoCredor` (Tarefa 1) e `normalizar` (Tarefa 1).
- Produz:
  - `classe_de_cobranca(nome_classe: str) -> bool`
  - `tipo_credor(nome: str) -> TipoCredor`. Quando um nome se encaixa em mais de um tipo, vale a ordem FUNDO > BANCO > EMPRESA > PESSOA.
  - `eh_empresa(nome: str, contexto: str = "") -> bool`: `True` se aparecer "CNPJ" até 80 caracteres depois do nome dentro de `contexto`. Se não aparecer, decide pelos marcadores no nome.
  - `partes_do_cabecalho(texto: str) -> tuple[list[str], list[str]]`: devolve `(credores, devedores)`, lidos dos rótulos `EXEQUENTE`/`AUTOR`/`REQUERENTE` e `EXECUTADO(A)`/`RÉU`/`REQUERIDO(A)`.

Classes da spec (seção 8, passo 2):
- **Entram:** Execução de Título Extrajudicial, Cumprimento de Sentença e Monitória.
- **Saem:** contra a Fazenda Pública, de alimentos e de ações coletivas; penal, execução da pena e fiscal; busca e apreensão; despejo; procedimento comum; embargos.

- [ ] **Passo 1: Escrever os testes que falham.** Os nomes de classe abaixo estão grafados como vêm na API (caixa misturada).

```python
@pytest.mark.parametrize("classe,esperado", [
    ("EXECUçãO DE TíTULO EXTRAJUDICIAL", True), ("CUMPRIMENTO DE SENTENçA", True), ("MONITóRIA", True),
    ("CUMPRIMENTO DE SENTENçA CONTRA A FAZENDA PúBLICA", False),
    ("CUMPRIMENTO DE SENTENçA DE OBRIGAçãO DE PRESTAR ALIMENTOS", False),
    ("Cumprimento de Sentença de Ações Coletivas", False), ("EXECUçãO FISCAL", False),
    ("EXECUçãO DA PENA", False), ("BUSCA E APREENSãO EM ALIENAçãO FIDUCIáRIA", False),
    ("DESPEJO POR FALTA DE PAGAMENTO CUMULADO COM COBRANçA", False),
    ("PROCEDIMENTO COMUM CíVEL", False), ("EMBARGOS à EXECUçãO", False)])
def test_classe_de_cobranca(classe, esperado): assert classe_de_cobranca(classe) is esperado

@pytest.mark.parametrize("nome,tipo", [
    ("BANCO SANTANDER (BRASIL) S.A.", TipoCredor.BANCO), ("Caixa Econômica Federal", TipoCredor.BANCO),
    ("COOPERATIVA DE CREDITO EXEMPLO - SICOOB", TipoCredor.BANCO),
    ("EXEMPLO CRÉDITO, FINANCIAMENTO E INVESTIMENTO S.A.", TipoCredor.BANCO),
    ("FIDC EXEMPLO NPL I", TipoCredor.FUNDO),
    ("EXEMPLO FUNDO DE INVESTIMENTO EM DIREITOS CREDITÓRIOS", TipoCredor.FUNDO),
    ("EXEMPLO SECURITIZADORA S.A.", TipoCredor.FUNDO),
    ("CONDOMÍNIO EDIFÍCIO EXEMPLO", TipoCredor.EMPRESA), ("LOJA EXEMPLO LTDA", TipoCredor.EMPRESA),
    ("JOÃO EXEMPLO DA SILVA", TipoCredor.PESSOA)])
def test_tipo_credor(nome, tipo): assert tipo_credor(nome) is tipo

def test_eh_empresa():
    assert eh_empresa("LOJA EXEMPLO LTDA") and eh_empresa("MARIA MODELO ME") and eh_empresa("J. EXEMPLO EIRELI")
    assert not eh_empresa("JOÃO EXEMPLO")
    assert eh_empresa("PROMOVE EXEMPLO", "FAZ SABER a PROMOVE EXEMPLO, CNPJ: 00.000.000/0001-00, que")
    assert not eh_empresa("ANA FICTÍCIA", "intimada ANA FICTÍCIA, CPF 000.000.000-00, para")

def test_partes_do_cabecalho():
    t = ("EXECUÇÃO DE TÍTULO EXTRAJUDICIAL Nº 1003464-18.2022.8.26.0269/SP RELATOR : FULANO RELATOR "
         "EXEQUENTE : BANCO EXEMPLO S.A. ADVOGADO(A) : CICRANO ADVOGADO (OAB SP000000) "
         "EXECUTADO : JOÃO EXEMPLO ADVOGADO(A) : BELTRANO (OAB SP000001) ATO ORDINATÓRIO Intime-se.")
    assert partes_do_cabecalho(t) == (["BANCO EXEMPLO S.A."], ["JOÃO EXEMPLO"])
    assert partes_do_cabecalho("AUTOR : ANA FICTÍCIA RÉU : LOJA EXEMPLO LTDA DESPACHO Vistos.") == (["ANA FICTÍCIA"], ["LOJA EXEMPLO LTDA"])
    assert partes_do_cabecalho("Vistos. Intime-se.") == ([], [])
```

- [ ] **Passo 2: Rodar e ver falhar**

Rodar: `pytest tests/djen/test_partes.py -v`
Esperado: FAIL.

- [ ] **Passo 3: Implementar `partes.py`**

Tudo é comparado em texto normalizado. Os marcadores ficam em constantes no topo do módulo:
- **Banco:** `banco`, `caixa economica`, `cooperativa de credito`, `sicoob`, `sicredi`, `financeira`, `credito, financiamento e investimento`.
- **Fundo:** `fidc`, `fundo de investimento`, `direitos creditorios`, `securitizadora`.
- **Empresa:** `ltda`, `s.a.`, `s/a`, `eireli`, `epp`, ` me` no fim, `mei`, `cia`, `condominio`, `associacao`, além dos marcadores de banco e de fundo.

No cabeçalho, o nome termina onde começa o próximo rótulo em maiúsculas seguido de `:` (`ADVOGADO(A) :`, `EXECUTADO :`…) ou uma palavra-chave de ato (`ATO ORDINATÓRIO`, `DESPACHO`, `DECISÃO`, `SENTENÇA`).

- [ ] **Passo 4: Rodar e ver passar**

Rodar: `pytest tests/djen -v`
Esperado: todos passam.

- [ ] **Passo 5: Commit**

```bash
git add src tests
git commit -m "feat: classify collection classes, creditors and debtors"
```

---

### Tarefa 5: Sinais e textos-padrão

**Arquivos:**
- Criar: `src/guicredito/djen/sinais.py`
- Teste: `tests/djen/test_sinais.py`

**Interfaces:**
- Consome: `Sinal` e `Bloco` (Tarefa 1); `frases` e `normalizar` (Tarefa 1).
- Produz:
  - `CATALOGO: list[tuple[str, Bloco, int, str, re.Pattern]]`, com os campos (chave, bloco, pontos, rótulo, regex sobre texto normalizado).
  - `eh_texto_padrao(frase_normalizada: str) -> bool`.
  - `detectar_sinais(texto: str) -> tuple[Sinal, ...]`:
    - analisa frase por frase e pula as frases de texto-padrão;
    - gera no máximo um `Sinal` por chave, o primeiro encontrado;
    - o `trecho` é a frase **original** (com acentos), cortada em 300 caracteres.

**Catálogo** (pontos da spec, seção 9; as frases são sintéticas):

| chave | bloco | pts | rótulo | tem que achar em | não pode achar em |
|---|---|---|---|---|---|
| `bloqueio_negativo` | DESGASTE | 10 | bloqueio infrutífero | "A pesquisa via SISBAJUD restou infrutífera." · "O bloqueio de ativos financeiros resultou negativo." | "Defiro a pesquisa via Sisbajud." |
| `acordo_frustrado` | DESGASTE | 10 | acordo frustrado | "A audiência de conciliação restou infrutífera." · "Não houve acordo entre as partes." | "Designo audiência de conciliação." |
| `arquivamento_provisorio` | DESGASTE | 8 | arquivamento provisório | "Remetam-se os autos ao arquivo provisório." | PADRAO_2 |
| `leilao_negativo` | PATRIMONIO | 20 | leilão negativo | "O leilão do imóvel restou negativo, por ausência de licitantes." | "Nomeio leiloeiro oficial." |
| `imovel_penhorado` | PATRIMONIO | 15 | imóvel penhorado/avaliado | "Lavre-se o termo de penhora do imóvel de matrícula nº 12.345." · "Juntado o laudo de avaliação do imóvel." | "Indique o exequente bens à penhora." |
| `bem_de_familia` | PATRIMONIO | 12 | bem de família | "Alega a executada tratar-se de bem de família." | — |
| `penhora` | PATRIMONIO | 6 | penhora | "Defiro a penhora on-line." | — |
| `veiculo` | PATRIMONIO | 4 | veículo | "Restrição via RENAJUD sobre o veículo." | PADRAO_3 |
| `superendividamento` | VULNERABILIDADE | 15 | superendividamento | "Repactuação com base na Lei 14.181/2021 (superendividamento)." | — |
| `gratuidade_devedor` | VULNERABILIDADE | 8 | justiça gratuita (devedor) | "Defiro ao executado os benefícios da justiça gratuita." | "Defiro ao exequente os benefícios da justiça gratuita." · PADRAO_1 |
| `defensoria` | VULNERABILIDADE | 8 | Defensoria Pública | "O executado é assistido pela Defensoria Pública." | — |
| `idoso` | VULNERABILIDADE | 8 | idoso(a) | "Anote-se a prioridade de tramitação, por ser a executada pessoa idosa." | — |
| `salario_impenhoravel` | VULNERABILIDADE | 6 | salário/aposentadoria impenhorável | "Os valores bloqueados são proventos de aposentadoria, impenhoráveis nos termos do art. 833, IV, do CPC." | "Comprove o executado a impenhorabilidade." |
| `sem_bens` | DESCONTO | −10 | ⚠ sem bens localizados | "Não foram localizados bens penhoráveis." · "Suspendo a execução nos termos do art. 921, III, do CPC." | "Suspendo o processo por 30 dias." |
| `prescricao_intercorrente` | DESCONTO | −10 | ⚠ prescrição intercorrente | "Manifeste-se o exequente sobre a prescrição intercorrente." | — |
| `devedor_nao_localizado` | ALERTA | 0 | ⚠ devedor não localizado | "Juntada de Carta pelo Correio - devolvida sem cumprimento" · "O executado não foi localizado no endereço indicado." · "Manifeste-se sobre a citação negativa." | — |

Textos-padrão **reais** do TJSP (caderno de 06/11/2026, sem nomes). Copie-os literalmente para `test_sinais.py`:

```python
PADRAO_1 = ('Caso seja fornecido novo endereço para a citação, com a manifestação deverá ser providenciado o '
            'recolhimento das custas respectivas - salvo se a parte for beneficiária da justiça gratuita - e o '
            'peticionamento eletrônico deverá observar o evento/tipo de documento "Pedido de citação em novo endereço".')
PADRAO_2 = ('No silêncio , será aplicado o disposto no artigo 485, § 1º, do Código de Processo Civil ou os autos '
            'serão remetidos ao arquivo provisório, conforme o caso.')
PADRAO_3 = ('Para viabilizar a realização da(s) pesquisa(s) eletrônica(s) requerida(s), deverá a parte interessada '
            'providenciar o(a): 1) recolhimento do valor ou, se o caso, a complementação correspondente à(s) pesquisa(s) '
            'eletrônica(s) pleiteada(s) ( Sisbajud, Renajud , Infojud , Serasajud , Comgasjud , Infoseg , Siel, CRCjud , '
            'Censec , SPCjud, ONR , Sniper, entre outras) , salvo se beneficiário da justiça gratuita , na quantia abaixo '
            'indicada ( com base na UFESP atualmente vigente ) , para cada pesquisa em cada pessoa/ CPF-CNPJ :')
```

- [ ] **Passo 1: Escrever os testes que falham**

Os testes vêm todos da tabela acima:
- `test_texto_padrao_nao_gera_sinal`: `detectar_sinais(" ".join([PADRAO_1, PADRAO_2, PADRAO_3])) == ()`.
- `test_sinal_detectado`, parametrizado pela coluna "tem que achar em": a chave aparece em `{s.chave for s in detectar_sinais(frase)}`, com o bloco, os pontos e o rótulo da tabela.
- `test_sinal_nao_detectado`, parametrizado pela coluna "não pode achar em": a chave **não** aparece.
- `test_um_sinal_por_chave`: um texto com duas frases de `penhora` gera um único `Sinal` `penhora`, com o trecho da primeira frase.
- `test_trecho_e_a_frase_original`: o trecho de "Alega a executada tratar-se de bem de família." mantém os acentos.

- [ ] **Passo 2: Rodar e ver falhar**

Rodar: `pytest tests/djen/test_sinais.py -v`
Esperado: FAIL.

- [ ] **Passo 3: Implementar `sinais.py`**

- `eh_texto_padrao` testa uma lista `PADROES` de regex sobre a frase normalizada. Comece com uma regex para cada texto acima:
  - `salvo se (a parte for )?beneficiari` + `justica gratuita`;
  - `no silencio` + `arquivo provisorio`;
  - `para viabilizar a realizacao da\(s\) pesquisa`.
- A Tarefa 10 acrescenta os textos-padrão novos que aparecerem.

- [ ] **Passo 4: Rodar e ver passar**

Rodar: `pytest tests/djen -v`
Esperado: todos passam.

- [ ] **Passo 5: Commit**

```bash
git add src tests
git commit -m "feat: detect case signals while skipping TJSP boilerplate"
```

---

### Tarefa 6: Montar os casos

**Arquivos:**
- Criar: `src/guicredito/djen/casos.py`
- Teste: `tests/djen/test_casos.py`

**Interfaces:**
- Consome: Tarefa 1 (modelos, `ano_cnj`, `normalizar`); Tarefa 4 (`partes_do_cabecalho`, `eh_empresa`, `tipo_credor`); Tarefa 5 (`detectar_sinais`).
- Produz:
  - `comarca(orgao: str) -> str`
  - `anos_citados(texto: str) -> tuple[int, ...]`
  - `resumir(pub: Publicacao) -> ResumoPublicacao`
  - `montar_casos(resumos: Iterable[ResumoPublicacao]) -> list[Caso]`

**Regras:**

- **`resumir`**
  - credores: destinatários com polo A, mais os credores do cabeçalho, sem repetir e na ordem em que aparecem;
  - devedores: destinatários com polo P, mais os devedores do cabeçalho, cada um como `Parte(nome, eh_empresa(nome, pub.texto))`;
  - sinais: `detectar_sinais(pub.texto)`;
  - `anos_citados(pub.texto)`.
- **`anos_citados`:** só números CNJ do TJSP (`\d{7}-\d{2}\.\d{4}\.8\.26\.\d{4}`) que venham até 20 caracteres depois de `processo principal`, `autos principais`, `autos de origem`, `processo de origem`, `autos (de )?n` ou `processo (de )?n`.
- **`montar_casos`**, agrupando por `numero_processo`:
  - classe, órgão, link, `ultima_data` e `ultimo_tipo` vêm do resumo mais recente; no empate, vale o último lido;
  - `n_publicacoes` = quantos resumos o processo tem;
  - tipo de credor: o de maior precedência entre todos os credores (FUNDO > BANCO > EMPRESA > PESSOA); `credor` é o primeiro nome desse tipo; sem credor nenhum, os dois ficam `None`;
  - devedores: juntar e tirar repetidos pelo nome normalizado. `pf` = as pessoas, `pj` = as empresas.
    - `devedor` = nomes de `pf` unidos por `"; "`, ou `None`;
    - `avalista` = tem `pf` e tem `pj`;
    - `so_empresa` = tem `pj` e não tem `pf`;
  - `ano_divida` = o menor entre `ano_cnj(numero)` e os anos citados que estejam entre 1980 e `ano_cnj(numero)`. Os posteriores são ignorados;
  - sinais: um por chave; com chave repetida, vale o do resumo mais recente;
  - `comarca(orgao)`.

- [ ] **Passo 1: Escrever os testes que falham**

```python
@pytest.mark.parametrize("orgao,esperado", [
    ("UPJ da 1ª a 4ª Varas Civeis da Comarca de Itapetininga", "Itapetininga"),
    ("1ª Vara Cível da Comarca de São Bernardo do Campo", "São Bernardo do Campo"),
    ("UPJ da 11ª a 15ª Varas Cíveis - Foro Central Cível", "São Paulo"),
    ("UPJ da 9ª a 14ª Varas Cíveis - Regional II - Santo Amaro", "São Paulo"),
    ("Central de Mandados - Taubaté", "Central de Mandados - Taubaté")])
def test_comarca(orgao, esperado): assert comarca(orgao) == esperado

def test_anos_citados():
    assert anos_citados("Conforme fls. 304 dos autos de n. 1030830-98.2015.8.26.0100, o trânsito") == (2015,)
    assert anos_citados("processo principal nº 0001234-56.2012.8.26.0100") == (2012,)
    assert anos_citados("(TJSP, Apelação Cível 1000001-11.2019.8.26.0001, Rel. Fulano)") == ()
    assert anos_citados("autos n. 0000001-11.2010.5.02.0001") == ()
```

Também com `ResumoPublicacao` montados à mão:
- `test_junta_publicacoes_do_mesmo_processo`: dois resumos (06/11 e 07/11) viram 1 caso, com `n_publicacoes == 2` e `ultima_data == date(2026, 11, 7)`.
- `test_devedor_vem_de_qualquer_publicacao`: o resumo 1 não tem devedor e o resumo 2 tem `Parte("JOÃO EXEMPLO", False)`. Resultado: `devedor == "JOÃO EXEMPLO"`.
- `test_devedor_nao_identificado`: sem devedores. Resultado: `devedor is None`, `so_empresa is False`, `avalista is False`.
- `test_so_empresa`: só `Parte("LOJA EXEMPLO LTDA", True)`. Resultado: `so_empresa is True`.
- `test_avalista`: `Parte("LOJA EXEMPLO LTDA", True)` e `Parte("JOÃO EXEMPLO", False)`. Resultado: `devedor == "JOÃO EXEMPLO"` e `avalista is True`.
- `test_fundo_prevalece_sobre_banco`: credores `("BANCO EXEMPLO S.A.", "FIDC EXEMPLO NPL I")`. Resultado: `tipo_credor is TipoCredor.FUNDO` e `credor == "FIDC EXEMPLO NPL I"`.
- `test_ano_divida_usa_o_mais_antigo`: número de 2022 com `anos_citados=(2015,)`. Resultado: `ano_divida == 2015`.
- `test_ano_citado_posterior_e_ignorado`: número de 2015 com `anos_citados=(2020,)`. Resultado: `ano_divida == 2015`.
- `test_resumir_junta_destinatarios_e_cabecalho`: publicação com destinatário `BANCO EXEMPLO S.A.` (polo A) e texto com `EXECUTADO : JOÃO EXEMPLO ADVOGADO(A) :`. Resultado: `credores == ("BANCO EXEMPLO S.A.",)` e `devedores == (Parte("JOÃO EXEMPLO", False),)`.

- [ ] **Passo 2: Rodar e ver falhar**

Rodar: `pytest tests/djen/test_casos.py -v`
Esperado: FAIL.

- [ ] **Passo 3: Implementar `casos.py`**

Regra de `comarca`:
1. Se houver `comarca de X`, devolve X, cortado no primeiro ` - ` ou `,`.
2. Senão, se houver `foro central` ou `regional`, devolve `"São Paulo"`.
3. Senão, devolve o `orgao` como veio.

- [ ] **Passo 4: Rodar e ver passar**

Rodar: `pytest tests/djen -v`
Esperado: todos passam.

- [ ] **Passo 5: Commit**

```bash
git add src tests
git commit -m "feat: group publications into cases with parties and debt age"
```

---

### Tarefa 7: Pontuar e ordenar

**Arquivos:**
- Criar: `src/guicredito/djen/pontuacao.py`
- Teste: `tests/djen/test_pontuacao.py`

**Interfaces:**
- Consome: `Caso`, `Pontuacao`, `CasoPontuado`, `Bloco` e `TipoCredor` (Tarefa 1).
- Produz:
  - `pontuar(caso: Caso, ano_atual: int) -> Pontuacao`
  - `ordenar(casos: Iterable[CasoPontuado], limite: int) -> list[CasoPontuado]`

**Valores (spec, seção 9):**
- **credor:** BANCO 20 · FUNDO 12 · PESSOA 8 · EMPRESA 5 · `None` 0.
- **idade** (`ano_atual - ano_divida`): 10 ou mais = 20 · 6 a 9 = 15 · 3 a 5 = 8 · menos de 3 = 0.
- **soma dos sinais por bloco, com teto:** DESGASTE 25 · PATRIMONIO 20 · VULNERABILIDADE 15.
- **descontos** (sem teto): soma dos sinais DESCONTO, mais **−15 se `devedor is None`**. ALERTA não conta.
- **total** = `max(0, credor + idade + desgaste + patrimonio + vulnerabilidade + descontos)`.
- **ordenação:** `total` decrescente, depois `ano_divida` crescente, depois `numero_processo` crescente. Corta em `limite`.

- [ ] **Passo 1: Escrever os testes que falham**

O helper `caso(**kw)` monta um `Caso` com estes padrões: banco, devedor "JOÃO EXEMPLO", `ano_divida=2016`, sem sinais. O helper `s(chave, bloco, pts)` monta um `Sinal`.

```python
def test_exemplo_completo():
    c = caso(sinais=(s("bloqueio_negativo", D, 10), s("imovel_penhorado", P, 15), s("gratuidade_devedor", V, 8)))
    assert pontuar(c, 2026) == Pontuacao(20, 20, 10, 15, 8, 0, 73)

@pytest.mark.parametrize("ano,pts", [(2016, 20), (2017, 15), (2020, 15), (2021, 8), (2023, 8), (2024, 0)])
def test_idade(ano, pts): assert pontuar(caso(ano_divida=ano), 2026).idade == pts

@pytest.mark.parametrize("tipo,pts", [(TipoCredor.BANCO, 20), (TipoCredor.FUNDO, 12), (TipoCredor.PESSOA, 8),
                                       (TipoCredor.EMPRESA, 5), (None, 0)])
def test_credor(tipo, pts): assert pontuar(caso(tipo_credor=tipo), 2026).credor == pts

def test_tetos_por_bloco():
    p = pontuar(caso(sinais=(s("a", D, 10), s("b", D, 10), s("c", D, 8), s("d", P, 20), s("e", P, 15),
                             s("f", V, 15), s("g", V, 8))), 2026)
    assert (p.desgaste, p.patrimonio, p.vulnerabilidade) == (25, 20, 15)

def test_descontos_e_alerta():
    p = pontuar(caso(devedor=None, sinais=(s("sem_bens", X, -10), s("prescricao_intercorrente", X, -10),
                                           s("devedor_nao_localizado", A, 0))), 2026)
    assert p.descontos == -35

def test_total_nunca_negativo():
    assert pontuar(caso(tipo_credor=None, devedor=None, ano_divida=2026,
                        sinais=(s("sem_bens", X, -10),)), 2026).total == 0

def test_ordenar_por_pontos_depois_ano_e_corta():
    ...  # três CasoPontuado: (80, 2020), (80, 2015), (50, 2010) com limite=2 → [(80, 2015), (80, 2020)]
```

(`D, P, V, X, A` = `Bloco.DESGASTE, PATRIMONIO, VULNERABILIDADE, DESCONTO, ALERTA`.)

- [ ] **Passo 2: Rodar e ver falhar**

Rodar: `pytest tests/djen/test_pontuacao.py -v`
Esperado: FAIL.

- [ ] **Passo 3: Implementar `pontuar` e `ordenar`**

Os pesos e os tetos ficam em constantes no topo de `pontuacao.py`.

- [ ] **Passo 4: Rodar e ver passar**

Rodar: `pytest tests/djen -v`
Esperado: todos passam.

- [ ] **Passo 5: Commit**

```bash
git add src tests
git commit -m "feat: score and rank cases"
```

---

### Tarefa 8: Gravar a planilha

**Arquivos:**
- Criar: `src/guicredito/djen/planilha.py`
- Teste: `tests/djen/test_planilha.py`

**Interfaces:**
- Consome: Tarefa 1 (modelos, `formatar_cnj`, `limpar_para_excel`).
- Produz: `escrever_planilha(caminho: Path, casos: list[CasoPontuado], publicacoes: dict[str, list[Publicacao]], resumo: ResumoRodada) -> None`. A pasta `caminho.parent` é criada se não existir.

**Formato (spec, seção 10):**

- **Abas, nesta ordem:** `Casos`, `Publicações`, `Como ler`.
- **Cabeçalho exato da aba `Casos`:** `#`, `Pontos`, `Processo`, `Início`, `Comarca`, `Classe`, `Credor`, `Tipo de credor`, `Devedor`, `Sinais de desgaste`, `Sinais de patrimônio`, `Sinais de vulnerabilidade`, `Última publicação`, `Publicações no período`, `Trecho principal`.
- **Regras das células da aba `Casos`:**
  - `Processo`: `formatar_cnj(numero)`, com hyperlink para `caso.link`.
  - `Início`: `ano_divida`.
  - `Tipo de credor`: o valor do enum. FUNDO vira `"Fundo ⚑"`. `None` vira `""`.
  - `Devedor`: `None` vira `"não identificado"`. Com `avalista`, vira `"{devedor} [avalista/sócio]"`.
  - `Sinais de desgaste`: os rótulos de DESGASTE, depois DESCONTO, depois ALERTA, unidos por `"; "`. Patrimônio e vulnerabilidade seguem a mesma regra, cada um com seu bloco.
  - `Última publicação`: `"06/11 · Intimação"`.
  - `Trecho principal`: `'"' + trecho + '"'` do sinal positivo de maior pontuação; no empate, o primeiro. Sem sinal positivo, `""`.
  - `Pontos`: fundo `FFC6EFCE` (verde) se ≥ 75; `FFFFEB9C` (amarelo) se entre 50 e 74; sem fundo abaixo de 50.
- **Aba `Publicações`:**
  - cabeçalho: `Processo`, `Data`, `Tipo`, `Órgão`, `Texto`;
  - uma linha por publicação dos processos da aba `Casos`, na ordem da aba `Casos` e depois por data;
  - texto com mais de 32.767 caracteres é cortado e termina com `"[texto cortado]"`, sem passar do limite.
- **Toda célula de texto** passa por `limpar_para_excel`.
- **Aba `Como ler`:**
  - uma linha por coluna da aba `Casos`, com a explicação;
  - a tabela de pontos da spec, seção 9;
  - o período, no formato `"03/11/2026 a 07/11/2026"`;
  - os cadernos usados (data, versão, total) e os dias sem caderno;
  - o funil: publicações lidas → de cobrança → processos → fora por serem só empresa → na planilha;
  - "Gerado em".
- **Abas `Casos` e `Publicações`:** cabeçalho congelado (`A2`) e autofiltro.

- [ ] **Passo 1: Escrever os testes que falham**

Cada teste grava em `tmp_path` e relê com `openpyxl.load_workbook`. Os testes são:
- `test_abas_e_cabecalho`: confere a ordem das abas e as 15 colunas exatas.
- `test_linha_do_caso`: um caso com 73 pontos, banco, 2016, avalista, desconto `sem_bens` e alerta. Confere:
  - `#`=1 e `Pontos`=73, com fundo amarelo;
  - `Processo` = `"1003464-18.2022.8.26.0269"`, com `hyperlink.target == caso.link`;
  - `Devedor` = `"JOÃO EXEMPLO [avalista/sócio]"`;
  - `Sinais de desgaste` = `"bloqueio infrutífero; ⚠ sem bens localizados; ⚠ devedor não localizado"`;
  - `Última publicação` = `"06/11 · Intimação"`;
  - `Trecho principal` = o trecho entre aspas do `imovel_penhorado`.
- `test_devedor_nao_identificado_e_fundo`: confere `"não identificado"` e `"Fundo ⚑"`.
- `test_cores_dos_pontos`: confere as cores de 75, 74, 50 e 49.
- `test_texto_longo_e_caracteres_de_controle`: uma publicação com 40.000 caracteres e um `"\x0b"` grava sem erro; a célula tem ≤ 32.767 caracteres, termina com `"[texto cortado]"` e não contém `"\x0b"`.
- `test_como_ler_tem_periodo_e_funil`: a aba contém `"03/11/2026 a 07/11/2026"` e os 5 números do funil.

- [ ] **Passo 2: Rodar e ver falhar**

Rodar: `pytest tests/djen/test_planilha.py -v`
Esperado: FAIL.

- [ ] **Passo 3: Implementar `escrever_planilha`**

A largura das colunas fica a seu critério. `Trecho principal` e os três campos de sinais usam quebra de linha automática.

- [ ] **Passo 4: Rodar e ver passar**

Rodar: `pytest tests/djen -v`
Esperado: todos passam.

- [ ] **Passo 5: Commit**

```bash
git add src tests
git commit -m "feat: write three-tab Excel workbook"
```

---

### Tarefa 9: Rodada completa e linha de comando

**Arquivos:**
- Criar: `src/guicredito/djen/pipeline.py`, `src/guicredito/djen/__main__.py`
- Teste: `tests/djen/test_pipeline.py`

**Interfaces:**
- Consome: todas as tarefas anteriores.
- Produz:
  - `rodar(inicio: date, fim: date, *, sigla: str = "TJSP", limite: int = 300, pasta_dados: Path = Path("dados/cadernos"), pasta_saida: Path = Path("saida"), cliente: ClienteHttp | None = None, agora: datetime | None = None) -> tuple[Path, ResumoRodada]`
  - `parse_args(argv: list[str]) -> argparse.Namespace`, com os campos `inicio: date`, `fim: date`, `limite: int` e `tribunal: str`.
  - `main(argv: list[str] | None = None) -> int`.

**Fluxo de `rodar`:**
1. Para cada `dias_uteis(inicio, fim)`, chamar `baixar_caderno`. Se vier `None`, pôr o dia em `dias_sem_caderno` e imprimir o aviso `"sem caderno em DD/MM"`.
2. **Primeira passada:** para cada ZIP, `ler_caderno`. Contar `publicacoes_lidas`. Quando `classe_de_cobranca(pub.classe)`, contar `publicacoes_cobranca` e guardar `resumir(pub)`.
3. `montar_casos`, que dá o número de `processos`. Separar os `so_empresa`, que dão `processos_so_empresa`. Pontuar com `ano_atual = agora.year` e chamar `ordenar(..., limite)`.
4. **Segunda passada:** ler os ZIPs de novo e guardar as `Publicacao` cujo número esteja entre os casos escolhidos.
5. `escrever_planilha(pasta_saida / f"casos_djen_{inicio}_a_{fim}.xlsx", ...)` e devolver o caminho e o resumo.

**Linha de comando:**
- `--inicio` e `--fim` no formato `AAAA-MM-DD`. Os dois juntos ou nenhum; só um dos dois é erro do argparse. Sem nenhum, vale `periodo_padrao(date.today())`.
- `--limite` (padrão 300). `--tribunal` (padrão `TJSP`).
- No fim, imprimir:

```
Dias com caderno: N (sem caderno: N)
Publicações lidas: N
Publicações de cobrança: N
Processos: N (só empresa, fora da planilha: N)
Casos na planilha: N
Planilha: <caminho>
```

- [ ] **Passo 1: Escrever os testes que falham**

Os testes usam `ClienteFalso` e ZIPs gerados com `fazer_zip`.

- `test_rodar_ponta_a_ponta`:
  - Dia 06/11, 5 itens, cada processo com `numero_processo` diferente, todos com ano 2022 no número:
    - (a) execução com banco no polo A, `JOÃO EXEMPLO` no polo P e texto "A pesquisa via SISBAJUD restou infrutífera.";
    - (b) execução com só `LOJA EXEMPLO LTDA` no polo P;
    - (c) busca e apreensão;
    - (d) execução fiscal;
    - (e) cumprimento de sentença com banco no polo A, sem devedor identificado.
  - Dia 09/11 (segunda): mais uma publicação do processo (a).
  - Período de 06/11 a 09/11.
  - Espera-se:
    - o arquivo existe;
    - `publicacoes_lidas == 6`, `publicacoes_cobranca == 4`, `processos == 3`, `processos_so_empresa == 1`, `casos_na_planilha == 2`;
    - (a) está na aba `Casos` com `Publicações no período` = 2, acima de (e);
    - a aba `Publicações` tem 3 linhas de dados.
- `test_rodar_pula_dia_sem_caderno`: período de 05/11 a 06/11, com 05/11 (quinta) sem metadados. Espera-se `dias_sem_caderno == [date(2026, 11, 5)]` e a planilha gerada.
- `test_rodar_respeita_limite`: com 3 casos válidos e `limite=1`, a aba `Casos` tem 1 linha de dados.
- `test_parse_args`:
  - `parse_args(["--inicio", "2026-11-03", "--fim", "2026-11-07"])` dá `inicio == date(2026, 11, 3)`, `limite == 300` e `tribunal == "TJSP"`;
  - `parse_args(["--inicio", "2026-11-03"])` lança `SystemExit`.

- [ ] **Passo 2: Rodar e ver falhar**

Rodar: `pytest tests/djen/test_pipeline.py -v`
Esperado: FAIL.

- [ ] **Passo 3: Implementar `pipeline.py` e `__main__.py`**

`__main__.py` só chama `raise SystemExit(main())`. O `main` usa `ClienteUrllib()`.

- [ ] **Passo 4: Rodar e ver passar**

Rodar: `pytest -v`
Esperado: todos os testes do projeto passam.

- [ ] **Passo 5: Commit**

```bash
git add src tests
git commit -m "feat: run full pipeline from the command line"
```

---

### Tarefa 10: Rodada real e textos-padrão novos

Esta tarefa usa a rede de verdade e lê dados reais. Não é TDD do código novo; é a calibração que a spec exige (seção 4: "planilha cheia de falsos positivos" é fracasso).

**Arquivos:**
- Modificar: `src/guicredito/djen/sinais.py` (lista `PADROES`)
- Modificar: `tests/djen/test_sinais.py` (novos textos-padrão como casos que não podem gerar sinal)

- [ ] **Passo 1: Rodar com o período padrão**

Rodar: `python -m guicredito.djen`
Esperado:
- baixa os 5 últimos dias úteis (~700 MB) para `dados/cadernos/`;
- imprime o resumo da Tarefa 9;
- cria `saida/casos_djen_<inicio>_a_<fim>.xlsx`.

Anote o tempo total.

- [ ] **Passo 2: Ler os 50 primeiros da aba `Casos`**

Para cada linha, confira se o `Trecho principal` e os sinais vêm de uma decisão de verdade ou de um texto-padrão. Anote cada falso positivo.

- [ ] **Passo 3: Fixar cada texto-padrão novo num teste**

Copie a frase da aba `Publicações` **sem nomes**: troque nomes por "FULANO EXEMPLO" e apague CPF, CNPJ e números de conta. Acrescente a frase como `PADRAO_n` na lista de casos de `test_texto_padrao_nao_gera_sinal`.

Rodar: `pytest tests/djen/test_sinais.py -v`
Esperado: FAIL no caso novo.

- [ ] **Passo 4: Acrescentar a regex em `PADROES` até o teste passar**

Rodar: `pytest -v`
Esperado: todos passam.

- [ ] **Passo 5: Rodar de novo**

Rodar: `python -m guicredito.djen`
Esperado: nenhum download, porque o cache é usado. Depois disso, repita os passos 2 a 5 até que os 50 primeiros não tenham sinal vindo de texto-padrão.

- [ ] **Passo 6: Conferir que nenhum dado real vai para o git**

Rodar: `git status --short`
Esperado: nada em `dados/` nem em `saida/`. Só mudanças em `src/` e `tests/`.

- [ ] **Passo 7: Commit**

```bash
git add src/guicredito/djen/sinais.py tests/djen/test_sinais.py
git commit -m "fix: ignore TJSP boilerplate found in the first real run"
```

- [ ] **Passo 8: Entregar ao Nick**

Informe:
- o caminho da planilha;
- o resumo impresso;
- o tempo da rodada;
- quantos textos-padrão novos foram acrescentados.

**Não mude pesos nem cortes.** Se o topo parecer errado por causa dos pesos, descreva o que viu e deixe a decisão com o Nick.
