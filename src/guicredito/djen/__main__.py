"""Entry point for ``python -m guicredito.djen``.

Python runs this file only when the package is started as a program. The
name ``guicredito.djen.pipeline`` is the other file in this folder,
``pipeline.py``. That file holds ``main``, which reads the dates, downloads
the cadernos, scores the cases, writes the workbook, and prints the summary.
This file does none of that work. It calls ``main`` and turns the number
``main`` returns (0) into the process exit code.
"""

from guicredito.djen.pipeline import main

raise SystemExit(main())
