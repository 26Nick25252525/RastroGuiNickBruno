# How to run

Python 3.12 or newer. From the project folder:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m guicredito.djen
```

The `.venv` in this checkout already exists. If it is there, only the last line is needed:

```bash
.venv/bin/python -m guicredito.djen
```

That downloads the TJSP DJEN cadernos for the last five weekdays through yesterday, keeps collection cases against a natural person, and writes the workbook. The first run takes a few minutes and downloads the zips. A later run of the same days reuses `dados/cadernos/` and still takes about three minutes, because it reads every publication. The terminal stays quiet until the summary.

The file is `saida/casos_djen_{inicio}_a_{fim}.xlsx`. Three tabs: Casos, Publicações, Como ler.

## Other dates

Pass both dates, or neither. One date alone is an error.

```bash
.venv/bin/python -m guicredito.djen --inicio 2026-11-03 --fim 2026-11-06
```

`--limite` is how many cases land on the sheet (default 300). `--tribunal` defaults to `TJSP`.

```bash
.venv/bin/python -m guicredito.djen --inicio 2026-11-03 --fim 2026-11-06 --limite 300 --tribunal TJSP
```

Weekends inside the range are skipped. A weekday with no caderno is printed as `sem caderno em dd/mm` and the run continues.

`dados/` and `saida/` hold names from the gazette. They stay on this machine.
