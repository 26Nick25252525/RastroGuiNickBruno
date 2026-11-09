from datetime import date

from guicredito.djen.leitura import ler_caderno
from guicredito.djen.modelos import Destinatario


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
    i = item(id=1, texto=None)
    del i["destinatarios"]
    p = next(ler_caderno(fazer_zip(tmp_path, "c", [[i]])))
    assert p.texto == "" and p.destinatarios == ()
