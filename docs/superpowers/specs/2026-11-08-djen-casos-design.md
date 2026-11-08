# Achador de casos de dívida no DJEN: design

- **Data:** 08/11/2026
- **Status:** rascunho para aprovação do Nick
- **Pesquisa anterior:** `ExecucoesSP_FontesEPlano.html` (26/10/2026)

Convenção do documento: o que o Nick decidiu aparece como **decisão do Nick**. O que eu decidi aparece como *(escolha minha)*, para ele poder conferir.

---

## 1. Intenção e porquê

O GUICredito quer encontrar **pessoas físicas em São Paulo cuja cobrança judicial travou**. São processos que se arrastam há anos: o credor (normalmente um banco) não consegue receber, não quer mais negociar, e a pessoa se desgastou e desistiu de tentar resolver. O ideal é que a pessoa tenha **algum patrimônio**. Nesta versão, sinal de patrimônio soma pontos mas não é obrigatório, e sinal de que não acharam bens tira pontos (**decisão do Nick**).

Com esses casos, o plano de negócio é o seguinte:

1. Procurar o credor.
2. Comprar a dívida com desconto (cessão de crédito).
3. Como novo credor, negociar com a pessoa em condições **menos agressivas** que as do banco.

O negócio ganha na diferença entre o preço pago e o acordo, e a pessoa ganha uma nova chance de negociar. O primeiro contato é sempre com o **credor**. Com o devedor, só depois, já como credor.

**Este projeto é só o primeiro passo:** um script que lê o Diário de Justiça Eletrônico Nacional (DJEN), separa os processos de cobrança com esse perfil e entrega uma **planilha Excel ordenada**. O Nick lê a planilha e escolhe de 10 a 20 casos para seguir adiante.

O documento de 26/10 descrevia o mesmo modelo de compra de crédito, olhando pelo lado do credor. A diferença agora está no **filtro de desgaste e vulnerabilidade** e na negociação menos agressiva.

## 2. Objetivos

- Um comando que baixa os cadernos do TJSP de um período, filtra os casos e gera um `.xlsx`.
- **Critério de sucesso:** na primeira rodada (5 dias úteis), o Nick encontra entre 10 e 20 casos bons para seguir adiante ao ler os primeiros colocados da planilha. *(Escolha minha: medir pela leitura dos 50 primeiros.)*

## 3. Fora desta versão (não-objetivos)

- Confirmar o patrimônio fora do diário (matrícula, IPTU, ONR).
- Histórico completo do processo via DataJud, que depende do advogado (ponto L7 do documento de 26/10).
- Rodar de forma agendada ou automática. Fica para depois; por ora, roda quando o Nick quiser.
- Outros tribunais e estados.
- Processos em que o devedor é só empresa.
- Busca e apreensão de veículo.
- Qualquer contato com devedores ou credores.

## 4. O que tornaria isto um fracasso mesmo funcionando (anti-objetivos)

- **Planilha cheia de falsos positivos.** Os textos-padrão do TJSP citam "justiça gratuita", "Sisbajud" e "arquivo provisório" de forma genérica (seção 7.3). Se isso pontuar, o topo da planilha vira lixo e o Nick para de confiar nela.
- **Vazamento de dados pessoais.** A planilha e os cadernos trazem nomes de pessoas físicas devedoras. Esses arquivos nunca vão para o git, nunca são enviados a serviços externos e ficam só na máquina do Nick.
- **Virar lista de abordagem.** O script só lê o diário oficial e gera uma lista de estudo. Ele não gera contatos, telefones, e-mails nem mensagens.
- **Raspar sites de tribunal** (e-SAJ etc.). O TJSP proíbe robôs. A única fonte é a API pública do DJEN.

## 5. Restrições

- **Fonte única:** API pública do DJEN (`comunicaapi.pje.jus.br`), sem login. Funcionando em 08/11/2026.
- **Onde será construído:** no **Cursor** (**decisão do Nick**). Este documento precisa se sustentar sozinho, sem o histórico da conversa em que foi escrito.
- **Linguagem:** Python 3. A máquina tem o Python 3.15.2. *(Escolha minha.)*
- **TDD:** os testes vêm antes da implementação (`rules/general.md` do claude_euler).
- **Git:** repositório próprio em `GUICredito/`, criado em `main`. O trabalho vai em `feature/djen-casos`, com commits no padrão convencional, verbo no presente e nenhum commit direto na `main`.
- **Volume:** cerca de 134 MB por dia de caderno do TJSP (06/11/2026: 225.016 publicações). Cinco dias dão cerca de 700 MB.
- **Ambiente:** nem o `openpyxl` nem o `pytest` estão instalados. Vão para um ambiente virtual do projeto (`.venv/`, ignorado pelo git). *(Escolha minha.)*

## 6. Decisões do Nick

| Tema | Decisão |
|---|---|
| Região | **São Paulo, TJSP.** *(Escolha minha: o estado inteiro, com coluna de comarca para filtrar a capital no Excel.)* |
| Busca e apreensão de veículo | **Não entra.** |
| Tipo de devedor | **Só pessoa física.** |
| Credor | **Qualquer um.** Banco ganha mais pontos. |
| Credor que já é fundo (FIDC) | **Aparece, com marcação.** |
| Uso no dia a dia | **Roda quando o Nick quiser.** Agendamento fica para depois. |
| Período da primeira rodada | **5 dias úteis.** |
| Escopo extra (DataJud, imóveis) | **Nada.** Só o diário. |
| Abas da planilha | **Casos + Publicações + Como ler.** As colunas do modelo foram aprovadas. |
| Repositório | **Próprio**, dentro de `GUICredito/`. |
| Devedor não identificado | **Entra marcado, com menos pontos.** *(Escolha minha: −15 pontos.)* |
| Patrimônio | **Não é obrigatório**, e o sinal de que não acharam bens **tira pontos**. *(Escolha minha: −10 pontos.)* |
| Pessoa física avalista ou sócia junto com empresa | **Entra, marcada "avalista/sócio".** |

## 7. A fonte: API do DJEN

### 7.1 O caderno do dia

```
GET https://comunicaapi.pje.jus.br/api/v1/caderno/{SIGLA}/{AAAA-MM-DD}/D
```

A resposta tem este formato (exemplo real, TJSP, 06/11/2026):

```json
{"tribunal": "Tribunal de Justiça do Estado de São Paulo", "sigla_tribunal": "TJSP",
 "meio": "D", "status": "Processado", "versao": 1, "data": "2026-11-06",
 "total_comunicacoes": 225016, "numero_paginas": 226, "tamanho_bytes": 134076065,
 "hash": "7abb0cb1…e392e", "url": "https://djen-prd.prd.s3.cnj.jus.br/cadernos/2026/11/06/TJSP-D-2026-11-06_v1.zip?…X-Amz-Expires=300…"}
```

- `url` é um link assinado que **expira em 300 segundos**. O download tem que ser feito logo; se o link expirar, basta pedir os metadados de novo.
- O ZIP traz `numero_paginas` arquivos `{SIGLA}-D-{data}_{k}.json`. Cada um tem `{"count": …, "items": [...]}` com até 1.000 publicações.
- `meio=D` é o diário. O `meio=E` é a Plataforma Nacional de Editais e fica fora.
- **Não verificado:**
  - se `hash` é o SHA-256 do ZIP;
  - o que a API devolve em fins de semana, feriados e dias sem caderno;
  - o que acontece quando um dia tem `versao` > 1 (republicação).

### 7.2 Campos de cada publicação dentro do caderno

`id`, `data_disponibilizacao`, `siglaTribunal`, `tipoComunicacao` (Intimação, Lista de distribuição, Pauta de julgamento, Ata de sessão, Citação, Edital), `nomeOrgao` (vara ou unidade), `texto` (HTML, às vezes começando com CSS solto como `body{…}`), `numero_processo` (20 dígitos, sem máscara), `meio`, `link` (documento no sistema do tribunal), `tipoDocumento`, `nomeClasse`, `codigoClasse`, `numeroComunicacao`, `ativo`, `hash`, `status`, `motivo_cancelamento`, `data_cancelamento`, `datadisponibilizacao`, `dataenvio`, `destinatarios[]` (`nome` e `polo`: A = ativo/credor, P = passivo/devedor), `destinatarioadvogados[]` (`advogado.nome`, `advogado.numero_oab`…).

O número CNJ segue o formato `NNNNNNN-DD.AAAA.J.TR.OOOO`. Nos 20 dígitos, as posições 10 a 13 trazem o **ano de início** do processo. `OOOO` é o código do foro.

Existe também a busca `GET /api/v1/comunicacao?siglaTribunal=…&dataDisponibilizacaoInicio=…&dataDisponibilizacaoFim=…&itensPorPagina=…&pagina=…`, mas ela devolve no máximo 10.000 resultados. Esta versão não usa essa busca.

### 7.3 O que os dados mostraram (TJSP, 06/11/2026, um dia)

| Medida | Valor |
|---|---|
| Publicações no dia | 225.016 |
| Em classes de cobrança, sem veículo | 56.171 |
| Processos distintos nessas classes | 52.527 |
| Devedor identificável (destinatário com polo P) | 49% |
| Devedor achado só no cabeçalho do texto (`EXECUTADO:`) | quase nada além do anterior |
| Dos devedores identificados, parecem pessoa física (pelo nome) | ~59% |
| Publicações com banco como destinatário | 13.798 |

**Textos-padrão.** Os atos ordinatórios do TJSP repetem trechos genéricos, por exemplo:

> "…salvo se beneficiário da justiça gratuita…"
> "…pesquisas eletrônicas (Sisbajud, Renajud, Infojud, Serasajud…)…"
> "…os autos serão remetidos ao arquivo provisório, conforme o caso…"

O Sisbajud aparece em 5.274 publicações de cobrança, mas só **33%** delas têm termo de resultado negativo. Uma palavra solta não serve como sinal.

**Contagem bruta de termos em um dia** (publicações de cobrança, antes de tirar os textos-padrão):

| Grupo | Termo | Publicações |
|---|---|---|
| Desgaste | Sisbajud / Bacenjud / teimosinha | 5.274 |
| | arquivamento provisório / sobrestado | 1.349 |
| | art. 921 | 1.328 |
| | infrutífero(a) | 1.133 |
| | ausência de bens | 717 |
| | prescrição intercorrente | 536 |
| | carta devolvida / não localizado | 336 |
| | "não houve acordo" e variações | 0 |
| Patrimônio | penhora | 7.691 |
| | veículo / Renajud | 4.957 |
| | imóvel | 2.921 |
| | avaliação | 1.868 |
| | leilão / hasta / praça | 614 |
| | matrícula | 529 |
| | bem de família | 70 |
| | leilão negativo / deserto | 12 |
| Vulnerabilidade | justiça gratuita / gratuidade | 3.620 |
| | salário / aposentadoria / proventos | 945 |
| | impenhorabilidade | 740 |
| | Defensoria | 530 |
| | idoso(a) / prioridade de tramitação | 97 |
| | superendividamento | 7 |
| Credor | banco (nome no texto) | 15.438 |
| | fundo / FIDC / direitos creditórios | 1.646 |
| | cessão de crédito / cessionário | 315 |

Em uma amostra de 4 publicações com todos os grupos de sinais, só 1 era o tipo de caso procurado: um processo de 2011 com dinheiro bloqueado na conta e discussão sobre impenhorabilidade. As outras três passaram por causa dos textos-padrão.

## 8. Como funciona

1. **Baixar.** Para cada dia útil do período, o script pede os metadados do caderno, baixa o ZIP e guarda em `dados/cadernos/`. Se o mesmo caderno, na mesma versão, já estiver lá, não baixa de novo.
2. **Filtrar por classe.**
   - Entram: **Execução de Título Extrajudicial**, **Cumprimento de Sentença** e **Monitória**.
   - Saem: cumprimento contra a Fazenda Pública, de alimentos e de ações coletivas; penal, execução da pena e fiscal; busca e apreensão; despejo; procedimento comum. *(Escolha minha para despejo e procedimento comum: despejo é sobre a moradia, e procedimento comum mistura de tudo.)*
3. **Agrupar por processo.** Todas as publicações do período com o mesmo `numero_processo` viram um caso só.
4. **Identificar as partes.**
   - Credor: destinatários com polo A, ou o cabeçalho do texto (`EXEQUENTE:`, `AUTOR:`).
   - Devedor: destinatários com polo P, ou o cabeçalho (`EXECUTADO:`, `RÉU:`, `REQUERIDO:`).
   - Tipo de credor: **banco/financeira**, **fundo** (FIDC, fundo de investimento, direitos creditórios, securitizadora), **pessoa** ou **empresa**.
   - Tipo de devedor: **pessoa física**, **empresa** ou **não identificado**. A classificação se baseia nos marcadores do nome (LTDA, S.A., ME, EIRELI etc.) e, quando aparecer, no CPF ou CNPJ do texto.
   - **Avalista/sócio:** quando o polo passivo tem empresa e pessoa física juntas, a pessoa física é o devedor mostrado, com a marcação "avalista/sócio" (**decisão do Nick**).
   - Os devedores de todas as publicações do processo no período são juntados. Basta uma publicação mostrar o devedor para o caso deixar de ser "não identificado".
5. **Filtro duro.**
   - Sai o processo cujo polo passivo tem **só** empresa(s).
   - Devedor não identificado **entra**, marcado e com desconto (**decisão do Nick**, seção 9).
6. **Sinais.** O script remove os textos-padrão conhecidos e só então procura as frases de cada grupo (seção 9).
7. **Pontuação** de 0 a 100 (seção 9).
8. **Planilha** (seção 10).

## 9. Sinais e pontuação

Isto é **ponto de partida**, para calibrar lendo o topo da primeira planilha. *(Pesos e limites são escolha minha.)*

| Bloco | Máximo | Como pontua |
|---|---|---|
| Credor | 20 | Banco/financeira: 20 · fundo: 12 (e marcado ⚑) · pessoa: 8 · empresa: 5 |
| Idade da dívida | 20 | 10 anos ou mais: 20 · 6 a 9 anos: 15 · 3 a 5 anos: 8 · menos de 3: 0 |
| Desgaste | 25 | Bloqueio ou pesquisa **com resultado negativo**: 10 · conciliação ou acordo frustrado: 10 · arquivamento provisório (fora do texto-padrão): 8 |
| Patrimônio | 20 | Leilão negativo/deserto: 20 · imóvel penhorado, matrícula ou avaliação de imóvel: 15 · bem de família alegado: 12 · penhora genérica: 6 · veículo: 4 |
| Vulnerabilidade | 15 | Superendividamento: 15 · gratuidade **deferida ao devedor**: 8 · Defensoria: 8 · idoso: 8 · salário/aposentadoria (impenhorabilidade): 6 |

Dentro de cada bloco, os pontos se somam até o máximo do bloco.

**Idade da dívida** *(escolha minha, a partir de ponto levantado na revisão)*. No TJSP, o cumprimento de sentença costuma ganhar um número CNJ novo, e o ano desse número é o do pedido de cobrança, não o da dívida. Por isso a idade usa o **ano mais antigo** entre:
- o número do próprio caso;
- os números CNJ do TJSP (`.8.26.`) citados nos textos do caso como processo principal ou autos principais. Exemplo visto nos dados: um cumprimento de 2022 cita "autos de n. 1030830-98.2015.8.26.0100".

A regra exata fica com quem construir. Precisa de testes, e citações de jurisprudência de outros processos **não** podem contar.

**Descontos e alertas.** Os descontos aparecem com ⚠ na coluna de desgaste, e a pontuação nunca fica abaixo de 0.

| Situação | Efeito | Origem |
|---|---|---|
| Ausência de bens / suspensão pelo art. 921 / execução frustrada | −10 | Desconto: **decisão do Nick**. Valor: escolha minha |
| Prescrição intercorrente (o crédito pode morrer, ruim para quem compra) | −10 | Escolha minha |
| Devedor não identificado | −15 | Desconto: **decisão do Nick**. Valor: escolha minha |
| Devedor não localizado / carta devolvida (negociação mais difícil) | 0, só alerta | Escolha minha |

Bloqueio de conta com resultado negativo continua **somando** como desgaste. Ele mostra que não acharam dinheiro na conta, o que não quer dizer que a pessoa não tenha bens.

**Regra obrigatória:** frases dentro de textos-padrão não pontuam. A implementação precisa de testes com trechos reais de texto-padrão (sem nomes) provando que eles **não** pontuam, e com trechos de decisões reais provando que **pontuam**.

## 10. A planilha

**Arquivo:** `saida/casos_djen_{inicio}_a_{fim}.xlsx`

### Aba "Casos"

Uma linha por processo, ordenada por pontos (decrescente). A aba traz os **300 melhores** casos *(escolha minha; ajustável na linha de comando)*.

| Coluna | Conteúdo |
|---|---|
| # | Posição |
| Pontos | 0 a 100, com cor: verde ≥ 75, amarelo 50–74 |
| Processo | Número com máscara, como link clicável (o `link` da publicação mais recente) |
| Início | Ano da dívida: o mais antigo (seção 9) |
| Comarca | Tirada do `nomeOrgao` (por exemplo, "Comarca de Itu" vira Itu, "Foro Central" vira São Paulo); se não der, o `nomeOrgao` inteiro |
| Classe | |
| Credor | Nome |
| Tipo de credor | Banco / Fundo ⚑ / Pessoa / Empresa |
| Devedor | Nome; "não identificado"; ou "Nome [avalista/sócio]" quando o polo passivo também tem empresa. *(Escolha minha: a marcação vai no texto da célula, sem coluna nova, e dá para filtrar no Excel por "contém".)* |
| Sinais de desgaste | Frases encontradas, incluindo os alertas ⚠ |
| Sinais de patrimônio | |
| Sinais de vulnerabilidade | |
| Última publicação | Data · tipo |
| Publicações no período | Quantidade |
| Trecho principal | A frase do sinal mais forte, entre aspas |

### Aba "Publicações"

Todas as publicações do período dos processos que estão na aba "Casos": processo, data, tipo, órgão e texto limpo (sem HTML). Como uma célula do Excel aceita no máximo 32.767 caracteres, textos maiores são cortados com a indicação "[texto cortado]".

### Aba "Como ler"

- O que é cada coluna.
- Como os pontos são calculados (a tabela da seção 9).
- O período coberto e os cadernos usados (data, versão, total de publicações).
- Quantos processos passaram em cada etapa do filtro.
- A data em que a planilha foi gerada.

## 11. Como roda

```
python -m guicredito.djen --inicio 2026-11-03 --fim 2026-11-07
```

- Sem `--inicio` e `--fim`, o período padrão são os **5 últimos dias úteis até ontem**.
- O tribunal está fixo em TJSP nesta versão. *(Escolha minha: deixar o parâmetro pronto para outros tribunais, sem testar nenhum outro.)*
- No fim, o terminal mostra um resumo: dias baixados, publicações lidas, casos em cada etapa e o caminho da planilha.

## 12. Dados pessoais

- `dados/` e `saida/` ficam no `.gitignore` desde o primeiro commit.
- Os **testes usam trechos sem nomes**: nomes trocados por fictícios e CPF/CNPJ removidos. Nenhum caderno real vai para o repositório.
- Nada é enviado para fora da máquina; a única conexão é o download da API do DJEN.

## 13. Pendente com o Nick

Nada. As três perguntas que vieram da revisão (devedor não identificado, patrimônio obrigatório, avalista/sócio) foram respondidas e estão nas seções 6, 8 e 9.

## 14. Deixado para quem construir

- A estrutura de pastas e módulos.
- A biblioteca HTTP: biblioteca padrão ou `requests`.
- O `openpyxl` para o Excel.
- As expressões exatas de cada sinal e a lista de textos-padrão, respeitando a regra da seção 9.
- Desempenho: ler os ZIPs em streaming, sem carregar tudo na memória.
- Mensagens de erro e retentativas: link expirado, erro 429/5xx, dia sem caderno.

## 15. Para depois (fora do código)

Perguntas para o advogado, do documento de 26/10:
- **L5:** LGPD de manter essa base.
- **L6:** limites do contato com o devedor para propor acordo.
- **L1:** como funciona a cessão de crédito em execução.

Também ainda não foi verificado se alguma regra da OAB se aplica à forma de oferecer a negociação.
