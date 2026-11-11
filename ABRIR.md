# Abrir a saída no Excel

No terminal do Mac, este comando abre a planilha da última rodada no aplicativo padrão do `.xlsx`:

```bash
open /Users/nick/Desktop/projects/claude_euler/projects/GUICredito/saida/casos_djen_2026-11-02_a_2026-11-06.xlsx
```

O caminho é absoluto, então funciona de qualquer pasta. Se o terminal já está na pasta do projeto, o mesmo arquivo abre assim:

```bash
open saida/casos_djen_2026-11-02_a_2026-11-06.xlsx
```

O nome segue as datas da rodada: `saida/casos_djen_{inicio}_a_{fim}.xlsx`. Troque as datas no comando quando a rodada for outra.

## Quatro endereços para testar

O caderno recente do DJEN abre como JSON. O PDF é o Diário do TJSP, e a edição que o botão ainda entrega é 22/07/2025. As publicações de agora se leem no site do Comunica.

1. Caderno do TJSP em 10/11/2026. A resposta é JSON, com o link do zip: https://comunicaapi.pje.jus.br/api/v1/caderno/TJSP/2026-11-10/D
2. PDF do Caderno 3, Capital, Parte I, de 22/07/2025: https://dje.tjsp.jus.br/cdje/downloadCaderno.do?dtDiario=22/07/2025&cdCaderno=12&tpDownload=D
3. PDF da Parte II do mesmo dia: https://dje.tjsp.jus.br/cdje/downloadCaderno.do?dtDiario=22/07/2025&cdCaderno=20&tpDownload=D
4. Site para ler uma publicação do DJEN, sem ser o arquivo do dia inteiro: https://comunica.pje.jus.br/
