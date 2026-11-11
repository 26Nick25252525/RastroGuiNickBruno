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
