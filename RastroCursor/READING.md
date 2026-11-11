# Where we are

Read this file first. It is the map of the collector built so far.

This repository downloads one edition of the São Paulo court gazette (DJE, Caderno 3, Capital) and turns each published act into a local record. There is no public API, no e-SAJ client, and no debt score yet.

The edition on disk is **22 July 2025**. The download for 6 November 2026 returned no edition. 22 July 2025 is the latest date that button still serves. Part I and Part II together produced **15,442 acts** (14,752 distinct case numbers).

The older research note that chose this source sits outside this repo: `/Users/nick/Desktop/projects/claude_euler/projects/GUICredito/ExecucoesSP_FontesEPlano.html`. Read it only if you need the wider source map. The files below are enough to see the collector.

## Read in this order

1. [READING.md](READING.md) — this page.
2. [pyproject.toml](pyproject.toml) — Python package name, dependencies (`httpx`, `pymupdf`, `pydantic`, `pytest`), and how the project is installed.
3. [.gitignore](.gitignore) — `data/` and the PDFs stay out of git. They hold party names from a public gazette.
4. [src/guicredito/dje/models.py](src/guicredito/dje/models.py) — the record shape: date, caderno code, page, CNJ number, court, full text, labeled parties, loose names, lawyers, keyword signals. There is no CPF field.
5. [src/guicredito/cli.py](src/guicredito/cli.py) — the two commands, `download` and `parse`.
6. [src/guicredito/dje/download.py](src/guicredito/dje/download.py) — opens the DJE index, then calls the official download button. Caderno 3 Capital is two files: code `12` (Part I) and code `20` (Part II). If the requested date has no edition, it walks backward to the latest one.
7. [src/guicredito/dje/parse.py](src/guicredito/dje/parse.py) — reads the PDF page by page. Distribution lists use fields (`PROCESSO`, `EXEQTE`, `EXECTDO`, `ADVOGADO`, `VARA`). Later acts are prose. A repeated case number stays in the same act.
8. [src/guicredito/dje/report.py](src/guicredito/dje/report.py) — counts and five examples. Names in the examples are replaced with letters.
9. [src/guicredito/__main__.py](src/guicredito/__main__.py) — lets you run `python -m guicredito`.
10. [tests/test_parse.py](tests/test_parse.py) — the behavior locked in with fake names: labeled parties, distribution-list fields, a prose act, no document field.
11. [tests/test_download.py](tests/test_download.py) — date formats and the “walk back to the latest edition” rule. No network.
12. [tests/test_report.py](tests/test_report.py) — the redacted example and the cap of five examples.
13. [tests/test_pdf_integration.py](tests/test_pdf_integration.py) — opens Part I only when a PDF is already in `data/raw/`, reads the first 40 pages, and checks that real case numbers come out.
14. [data/reports/2025-07-22.md](data/reports/2025-07-22.md) — the result of this edition. Read this before the JSONL. It is counts, not a list of people.
15. [data/parsed/2025-07-22.jsonl](data/parsed/2025-07-22.jsonl) — one JSON object per line, 15,442 lines. Part I is `"caderno": "12"` (11,359 acts). Part II is `"caderno": "20"`. Open a few lines. Do not try to read the file straight through.
16. [data/raw/2025-07-22_12.pdf](data/raw/2025-07-22_12.pdf) — the Part I download (1,237 pages). Same bytes as https://dje.tjsp.jus.br/cdje/downloadCaderno.do?dtDiario=22/07/2025&cdCaderno=12&tpDownload=D
17. [data/raw/2025-07-22_20.pdf](data/raw/2025-07-22_20.pdf) — the Part II download (391 pages). Same bytes as https://dje.tjsp.jus.br/cdje/downloadCaderno.do?dtDiario=22/07/2025&cdCaderno=20&tpDownload=D

## What Part I actually yielded

The Part I PDF is the Capital first-instance gazette for that day, mostly distribution lists for the central courthouses, plus prose acts later in the file. From it the parser kept:

- 11,359 acts, 9,595 with a labeled role
- execução: 2,385
- citação: 254
- cumprimento de sentença: 174
- acordo: 74
- homologação: 23
- transação: 12
- avaliação: 11
- penhora: 8
- hasta, adjudicação, arresto: none in this file

The courts with the most acts in Part I are criminal enforcement and state tax enforcement. A civil credit that could be purchased is inside the file. It is not most of the file.

## Commands

```bash
.venv/bin/python -m guicredito download --date 2026-11-06
.venv/bin/python -m guicredito parse --date 2025-07-22
.venv/bin/pytest -q
```

`download` prints the date it actually saved when the requested day has no edition.

## Skip these

- `.venv/` — installed packages
- `src/**/__pycache__/` and `tests/**/__pycache__/` — bytecode
- `.pytest_cache/` — pytest’s own cache

## Not built yet

DataJud, the auction caderno (code `14`), CNPJ, property records, protest records, a score, and any HTTP API on top of the JSONL.
