"""The DJEN command: download TJSP gazettes and write the case workbook.

This folder is one step per file. ``__main__.py`` only starts the program.
``pipeline.py`` calls the others in order: ``fonte`` downloads each caderno,
``leitura`` reads it, ``partes`` and ``sinais`` inspect each act, ``casos``
groups acts into one case per process, ``pontuacao`` ranks them, and
``planilha`` writes the Excel file. ``modelos`` holds the data those files
pass to each other. ``texto`` holds the small string tools they share.
"""
