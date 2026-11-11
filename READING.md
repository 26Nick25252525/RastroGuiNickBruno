# Where to read

Read this file first. It is the map of the command you just ran.

The command downloads five business days of the São Paulo court gazette from the national DJEN API, keeps collection cases against a natural person, scores them, and writes an Excel file. One run produced `saida/casos_djen_2026-11-02_a_2026-11-06.xlsx` (300 cases).

`RastroCursor/` is an earlier experiment that reads the old PDF gazette. It has its own `READING.md`. It is not this command. Start in `src/guicredito/djen/`.

## Read in this order

The first four files are the whole story. The rest are one step each, in the order `rodar` calls them.

1. [READING.md](READING.md) — this page.
2. [docs/superpowers/specs/2026-11-08-djen-casos-design.md](docs/superpowers/specs/2026-11-08-djen-casos-design.md) — sections 1 and 2 only. Why the sheet exists: stalled collection cases against a person, so a creditor can be approached later. Stop there on the first pass.
3. [pyproject.toml](pyproject.toml) — Python package, and the only dependencies: `openpyxl` and `pytest`.
4. [src/guicredito/djen/__main__.py](src/guicredito/djen/__main__.py) — four lines. `python -m guicredito.djen` calls `main`.
5. [src/guicredito/djen/pipeline.py](src/guicredito/djen/pipeline.py) — read `rodar` (line 16) slowly. It is the whole pipeline in one function: download each weekday, count publications, keep collection classes, build cases, drop company-only debtors, score, cut at 300, read the full text of the winners a second time, write the workbook. Then read `main` (line 106) for the lines the terminal printed.
6. [src/guicredito/djen/modelos.py](src/guicredito/djen/modelos.py) — the nouns. `Publicacao` is one act in the gazette. `ResumoPublicacao` is that act after parties and signals are pulled out. `Caso` is every act of one process number folded together. `CasoPontuado` is a case plus its score. `ResumoRodada` is the funnel the terminal printed.

Then follow the steps inside `rodar`:

7. [src/guicredito/djen/fonte.py](src/guicredito/djen/fonte.py) — which days, and how a caderno zip lands in `dados/cadernos/`. `periodo_padrao` walks back five weekdays from yesterday. `baixar_caderno` asks the API, checks the SHA-256, and reuses the zip when the hash still matches. A 404 is a day with no caderno.
8. [src/guicredito/djen/leitura.py](src/guicredito/djen/leitura.py) — one zip becomes a stream of `Publicacao`. Cancelled acts are skipped. The text is still the full HTML-stripped act.
9. [src/guicredito/djen/texto.py](src/guicredito/djen/texto.py) — small tools the later files all use. `normalizar` strips accents and lowercases, so every regex is written against that form. `frases` splits sentences without breaking `art. 921` or a CNJ number. `formatar_cnj` is what the Processo column shows. `ano_cnj` is the year inside the case number.
10. [src/guicredito/djen/partes.py](src/guicredito/djen/partes.py) — two jobs. `classe_de_cobranca` decides whether the act is a collection case at all (execução de título, cumprimento de sentença, monitória; fiscal, alimentos, busca e apreensão, and the rest of `_FORA` are out). `eh_empresa`, `tipo_credor`, and `partes_do_cabecalho` decide who the creditor and the debtor are. A CNPJ counts only for the name it follows.
11. [src/guicredito/djen/sinais.py](src/guicredito/djen/sinais.py) — read `PADROES` first, then `CATALOGO`, then `detectar_sinais`. Boilerplate TJSP sentences are masked. What remains can become one signal per key: wear, assets, vulnerability, a discount, or an alert. The points in `CATALOGO` are the points on the sheet.
12. [src/guicredito/djen/casos.py](src/guicredito/djen/casos.py) — `resumir` handles one publication. `montar_casos` groups them by process number. The newest act supplies class, court, and link. The creditor is the highest-precedence name (fund, then bank, then company, then person). `ano_divida` is the case year, or an older case number the text cites. `so_empresa` is what `rodar` throws away before scoring.
13. [src/guicredito/djen/pontuacao.py](src/guicredito/djen/pontuacao.py) — short. Creditor points, age points, three block caps, discounts with no cap, then `ordenar`: highest total, then older debt, then process number, then cut at the limit.
14. [src/guicredito/djen/planilha.py](src/guicredito/djen/planilha.py) — the three tabs. `_COLUNAS` is the Casos header. `_aba_casos`, `_aba_publicacoes`, and `_aba_como_ler` each fill one sheet. Green is 75 or more. Yellow is 50 to 74.

Tests, after the module they lock in. They use the fictional names JOÃO EXEMPLO and BANCO EXEMPLO S.A. and never touch the network.

15. [tests/djen/conftest.py](tests/djen/conftest.py) — `item()` builds one fake publication. `fazer_zip()` packs a fake caderno. `ClienteFalso` stands in for the API.
16. [tests/djen/test_pipeline.py](tests/djen/test_pipeline.py) — one fake week, end to end. Read this test once `rodar` is familiar. It shows which classes survive and which process lands on the sheet.
17. The other tests sit beside their module: `test_texto.py`, `test_leitura.py`, `test_fonte.py`, `test_partes.py`, `test_sinais.py`, `test_casos.py`, `test_pontuacao.py`, `test_planilha.py`. Open one when the matching source file is unclear.

The result, last:

18. [saida/casos_djen_2026-11-02_a_2026-11-06.xlsx](saida/casos_djen_2026-11-02_a_2026-11-06.xlsx) — the workbook from the run. Casos is the ranked list. Publicações is the raw text of those 300 cases. Como ler explains each column and repeats the points table.

## Second pass

Come back to the spec when you want the rule behind a number, not the code that applies it.

- Sections 7 and 8 of [the spec](docs/superpowers/specs/2026-11-08-djen-casos-design.md) — the API and which classes are in.
- Section 9 — the points, the caps, and the sort. Those numbers are copied into `pontuacao.py` and `sinais.py`.
- Section 10 — what each Excel column must contain.

[docs/superpowers/plans/2026-11-08-djen-casos.md](docs/superpowers/plans/2026-11-08-djen-casos.md) is the build recipe (ten tasks). Read it to see how the code was written. You do not need it to see what the code does.

`dados/cadernos/` holds the downloaded zips, about 700 MB for those five days. Leave them closed. The code reads them. Git ignores `dados/` and `saida/` because both contain names from the gazette.
