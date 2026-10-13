# Eleições Brasil — manual de uso

Este manual reúne os comandos para baixar os arquivos do TSE, carregar os boletins no Postgres e abrir o relatório de poder dos partidos. Rode tudo na raiz do projeto.

O ano de trabalho é 2026. Outro ano entra pelo `--ano`, sem alterar o código.

## Preparar o ambiente

Você precisa do [uv](https://docs.astral.sh/uv/) e do Docker.

```bash
cp .env.example .env
uv sync
```

No `.env`, deixe `ANO_ELEICAO=2026`. O exemplo do repositório traz `2022` só como ilustração. `--ano` na linha de comando prevalece sobre essa variável.

`DIRETORIO_SAIDA` é opcional. Sem ela, os arquivos vão para `downloads/{ano}/`.

## Subir o banco

```bash
make up
```

O comando sobe o Postgres, o Metabase, o Adminer e a API. As portas no seu computador usam o prefixo 1:

| Serviço | Endereço |
| --- | --- |
| Postgres | `127.0.0.1:15432` |
| Metabase | http://localhost:13000 |
| Adminer | http://localhost:18080 |
| API | http://localhost:15000 |

Usuário, banco e senha locais: `eleicoes`. Dentro do Docker o host do banco é `postgres` e a porta é `5432`.

Para parar os contêineres:

```bash
make down
```

> **Aviso:** preserve o volume `postgres_data`. Um `docker compose down -v` apaga os boletins já importados.

Consulta direta:

```bash
PGPASSWORD=eleicoes psql -h 127.0.0.1 -p 15432 -U eleicoes -d eleicoes
```

## Baixar os zips de dados abertos

```bash
uv run python -m eleicoes download --ano 2026
```

O comando baixa correspondências (`CESP_*`) e logs GEDAI. Em 2026 o pacote clássico de totalização responde 404 e fica de fora. Arquivo que já existe e tem tamanho maior que zero é ignorado.

Opções:

| Opção | Efeito |
| --- | --- |
| `--ano` | Ano da eleição. Sem ela, vale `ANO_ELEICAO`. |
| `--destino` | Pasta de saída. Padrão: `downloads/{ano}`. |

Os zips ficam em `downloads/{ano}/{conjunto}/turno-{n}/{UF}/`. Ao final, `downloads/{ano}/indice.csv` lista o que foi baixado.

Saída do processo: `0` quando a busca termina, `2` quando a eleição não existe, `1` em falha de rede ou de disco.

## Baixar os arquivos de urna

Para o 1º turno de 2026, uma UF de cada vez, com log:

```bash
uv run python scripts/baixar_urnas_2026.py
```

O script percorre todas as siglas, inclusive `ZZ` (Exterior). Arquivo já gravado é ignorado e a rodada seguinte continua de onde parou. Uma segunda cópia encontra `logs/urnas-2026/execucao.lock` e não inicia.

Para deixar o download se recuperar sozinho:

```bash
uv run python scripts/manter_urnas_2026.py
```

Cada falha espera 3 minutos e o download recomeça. Arquivo já gravado continua ignorado. Uma segunda cópia encerra com a mensagem `Já existe uma execução deste script.` O acompanhamento fica em `logs/urnas-2026/resumo.log`.

Uma UF só, sem o script nacional:

```bash
uv run python -m eleicoes urnas --ano 2026 --turno 1 --uf DF
```

| Opção | Efeito |
| --- | --- |
| `--ano` | Ano da eleição. |
| `--turno` | `1` ou `2`. Pode repetir. Sem esta opção, o comando pede os dois turnos. |
| `--uf` | Sigla. Pode repetir. Sem esta opção, pede todas as UFs. |
| `--destino` | Pasta de saída. Padrão: `downloads/{ano}`. |

O script nacional fixa 2026 e o turno 1. Use-o para a varredura do país. Use `eleicoes urnas` quando quiser uma UF ou um turno específico.

Os arquivos de cada seção vão para:

```text
downloads/{ano}/arquivo-urna/turno-{turno}/{UF}/{municipio}/{zona}/{secao}/
```

O ritmo fica em 80 requisições por segundo. O TSE corta o endereço acima de 100 requisições em um segundo. Até 16 seções baixam ao mesmo tempo.

Saída: `0` quando a UF termina, `2` quando o turno ainda não foi publicado, `1` em falha de rede, bloqueio ou ausência repetida do índice.

Importe os boletins de uma UF depois que `logs/urnas-2026/resumo.log` registrar `fim UF saída=0`.

> **Aviso:** um download que já está rodando continua com o código que estava na memória quando ele começou. A face nova vale na próxima partida. Deixe o processo atual concluir.

### Ler o progresso

Cada seção pronta aparece em um bloco. A barra é a seção em andamento. Em seguida vêm os arquivos daquela seção:

```text
[  80,1% --------.. ] DF 97012  zona 0004  seção 0394
[baixado] o03220df9701200040394-bu.dat
[baixado] o03220df9701200040394-log.jez
[ignorado] o03220df9701200040394-rdv.dat
[ausente] o03220df9701200040394-imgbu.dat
```

`[baixado]` gravou o arquivo. `[ignorado]` já estava no disco. `[ausente]` o TSE anunciou o arquivo e respondeu 404. A última seção da UF fecha em `100,0%`.

### Tratar arquivo ausente

Um 404 de arquivo de seção grava um marcador vazio ao lado do nome original, por exemplo `imgbu.dat.ausente`. O download segue. Três ausências de arquivo de seção não interrompem a UF.

Um 404 do índice ou do JSON auxiliar, depois de três ocorrências, interrompe a UF. A mensagem de bloqueio por excesso de requisições é outra: `O TSE bloqueou o endereço por excesso de requisições.`

## Importar as correspondências

No computador, depois do download dos zips:

```bash
uv run python -m eleicoes import --ano 2026 --origem downloads/2026
```

Pelo Docker, com os downloads montados em `/data/downloads`:

```bash
make import
```

Entram só os CSV de correspondência (`csec_` e `ccont_`). Binários de urna são ignorados. Rodar de novo substitui a carga daqueles arquivos.

| Opção | Efeito |
| --- | --- |
| `--ano` | Ano da eleição. |
| `--origem` | Pasta que contém `indice.csv`. Padrão: `downloads/{ano}`. |

Saída: `0` quando ao menos um CSV entra e nenhum falha, `2` quando não há índice ou membro tabular, `1` em esquema divergente, zip ilegível ou falha de banco.

## Importar os boletins

Um estado por vez. `--turno` e `--uf` são obrigatórios.

```bash
uv run python -m eleicoes boletins --ano 2026 --turno 1 --uf DF
```

O comando lê cada `*-bu.dat` da UF, apaga a fatia anterior daquele ano, turno e UF e grava a nova em uma transação. A segunda execução substitui a carga. As outras UFs permanecem. Um arquivo inválido não grava nada dessa UF.

O sucesso sem ausência termina assim:

```text
Boletins gravados: 1281. Votos: 11924.
```

Se existirem marcadores `.ausente`, cada nome aparece antes desse resumo:

```text
[ausente] o03220ma0843500500102-imgbu.dat
Boletins gravados: 7101. Votos: 685455.
```

A importação usa apenas `bu.dat`. `imgbu.dat`, `rdv.dat`, `log.jez` e `vota.vsc` ficam no disco.

Saída: `0` quando a UF é gravada, `2` quando não há `bu.dat`, `1` em boletim inválido ou falha de banco.

`ZZ` é o Exterior. Importe essa sigla para o total nacional de presidente incluir o voto no exterior. Na tabela de estados a linha se chama Exterior. `ZZ` não entra nas regiões.

## Listar arquivos ausentes

```bash
uv run python -m eleicoes ausentes --ano 2026 --turno 1
```

Uma UF:

```bash
uv run python -m eleicoes ausentes --ano 2026 --turno 1 --uf MA
```

O comando só lê os marcadores `.ausente` que já estão no disco. Ele não chama o TSE e não grava voto. `--turno` é obrigatório.

| Situação | Arquivo |
| --- | --- |
| Todas as UFs | `relatorios/ausentes-2026-turno-1.txt` |
| Uma UF | `relatorios/ausentes-2026-turno-1-ma.txt` |

Cada linha é o caminho a partir da pasta do ano, sem o sufixo `.ausente`. Exemplo: `arquivo-urna/turno-1/MA/08435/0050/0102/o03220ma0843500500102-imgbu.dat`. Sem marcadores, o arquivo sai vazio e o terminal mostra `Nenhum arquivo ausente.`

## Abrir o relatório de poder

```bash
uv run python scripts/relatorio_poder.py --ano 2026 --turno 1 --cargo presidente
```

O navegador abre o HTML. Para só gravar o arquivo:

```bash
uv run python scripts/relatorio_poder.py --ano 2026 --turno 1 --cargo presidente --sem-navegador
```

O arquivo sai em `relatorios/{uf}-{ano}-turno-{turno}-{cargo}.html`. Sem `--destino` e sem `--uf`, o nome usa `ac` porque a UF padrão do arquivo é `AC`. O conteúdo reúne os municípios, os estados, as regiões e o país a partir das UFs já importadas. `--uf` escolhe o nome do arquivo. Ela não corta as tabelas.

| Opção | Padrão | Efeito |
| --- | --- | --- |
| `--ano` | `2026` | Ano da eleição. |
| `--turno` | `1` | Turno. |
| `--uf` | `AC` | Sigla usada no nome do arquivo. |
| `--cargo` | `deputadoFederal` | Cargo da grade. |
| `--destino` | pasta `relatorios/` | Caminho completo do HTML. |
| `--sem-navegador` | abre o navegador | Grava o HTML e deixa o navegador fechado. |
| `--atualizar` | usa o que está no banco | Recalcula as grades e substitui as linhas guardadas. |

Cargos usados nas grades: `presidente`, `governador`, `senador`, `deputadoFederal`, `deputadoEstadual`. No Distrito Federal a coluna estadual é `deputadoDistrital`.

O banco guarda as células da grade: lugar, comparecimento, partido, votos nominais e votos de legenda. Cada apresentação monta o HTML de novo. A primeira execução calcula a partir dos boletins e grava as células. A seguinte carrega essas linhas e mostra `Relatório carregado do banco, gerado em AAAA-MM-DD HH:MM.`

Depois de importar uma UF nova, peça o recálculo:

```bash
uv run python scripts/relatorio_poder.py --ano 2026 --turno 1 --cargo presidente --atualizar
```

O percentual exibido é o voto do partido sobre os votos válidos, com arredondamento metade para cima e duas casas. No cargo `presidente`, o número digitado sem candidato entra como nulo. A escala de cor é única para a grade inteira. O cabeçalho de cada coluna ordena a tabela.

### Usar a página

- **Claro** e **Escuro** trocam o tema.
- Um clique no cabeçalho ordena a coluna. Lugar usa a ordem do português. As demais colunas usam o valor numérico.
- `K` liga e desliga o laser. `Esc` solta o laser.
- `M` liga e desliga o marca-texto. Ao desligar, os realces saem da página.
- Com o laser ou o marca-texto ligado, o clique desenha. A ordenação e o tema ficam para quando a ferramenta estiver desligada.

O relatório sai com quatro recortes: por município (uma tabela por UF), por estado, por região e no país. As linhas de país e de região somam as UFs já carregadas. O Exterior aparece na tabela de estados e no total do país depois da importação de `ZZ`.

## Cruzar presidente e governador

O relatório compara, em cada lugar, o partido líder do governador com o primeiro e o segundo da presidência e mostra a margem presidencial. A leitura é do lugar, a soma das seções, e não do eleitor.

```bash
uv run python scripts/relatorio_presidente_governador.py --ano 2026 --turno 1
```

Para só gravar o arquivo:

```bash
uv run python scripts/relatorio_presidente_governador.py --ano 2026 --turno 1 --sem-navegador
```

O arquivo sai em `relatorios/{uf}-{ano}-turno-{turno}-presidente-governador.html`. Sem `--destino` e sem `--uf`, o nome usa `ac`. `--uf` valida a sigla e entra no nome do arquivo. Ela não corta as tabelas. `--destino` troca o caminho. `--atualizar` ignora o que está no banco, relê os boletins e substitui as linhas.

O banco guarda os votos municipais dos dois cargos e os brancos e nulos de cada cédula. O HTML é montado em cada apresentação. A primeira execução calcula a partir dos boletins e grava essas células. A seguinte carrega as linhas e mostra `Relatório carregado do banco, gerado em AAAA-MM-DD HH:MM.`

A página tem duas leituras. A composição conta os municípios de cada classe e soma os votos válidos de presidente. A participação usa esse total, inclusive as cidades sem governador. Ao lado ficam os totais de brancos e de nulos de presidente. As tabelas Por município, Por estado, Por região e No país recalculam o líder pela soma dos votos. A região deixa o Exterior de fora. O país inclui todas as UFs carregadas.

| Classe | Leitura |
| --- | --- |
| Consolidação | O partido do governador é o líder da presidência. |
| Terreno de virada | O partido do governador é o segundo da presidência. |
| Em aberto | O partido do governador é um terceiro partido. |
| Sem governador | Há líder de presidente e não há líder de governador. O Exterior entra aqui quando não tem voto de governador. |

Brancos e nulos aparecem na linha do lugar e ficam de fora do percentual, da margem e da classe. Esses três usam só os votos válidos. O número digitado sem candidato a presidente conta como nulo.

## Abrir o mapa de presidente ou de governador

O mapa pinta o partido líder em cada recorte. O zoom mínimo é o país, o seguinte é a UF e o máximo é o município. A região não entra: a malha desse recorte ainda não foi medida.

Antes da primeira página, grave a malha medida:

```bash
uv run python scripts/baixar_malha.py
```

Coloque as cores e as logomarcas em `downloads/malha/marcas.json` e `downloads/malha/logomarcas/`. A chave é o número do partido. O valor tem `cor` (`#` e seis dígitos) e `arquivo` (o nome do PNG ou do SVG). Sem a cor ou a logomarca de um líder, o comando para e não escreve o HTML.

```bash
uv run python scripts/relatorio_mapa.py --ano 2026 --turno 1 --cargo presidente
```

Para só gravar o arquivo:

```bash
uv run python scripts/relatorio_mapa.py --ano 2026 --turno 1 --cargo governador --sem-navegador
```

O arquivo sai em `relatorios/mapa-{cargo}-{ano}-turno-{turno}.html`. `--atualizar` relê os boletins e substitui os votos municipais que o relatório de presidente e governador também usa.

| Opção | Padrão | Efeito |
| --- | --- | --- |
| `--ano` | `2026` | Ano da eleição. |
| `--turno` | `1` | Turno. |
| `--cargo` |  | `presidente` ou `governador`. |
| `--destino` | pasta `relatorios/` | Caminho completo do HTML. |
| `--sem-navegador` | abre o navegador | Grava o HTML e deixa o navegador fechado. |
| `--atualizar` | usa o que está no banco | Recalcula os votos municipais. |

## Entender os arquivos da seção

| Arquivo | Papel neste projeto |
| --- | --- |
| `bu.dat` | Boletim estruturado. É a fonte dos votos e do relatório. |
| `imgbu.dat` | Imagem do boletim impresso. Fica no disco. A ausência dela preserva os votos. |
| `rdv.dat` | Registro Digital do Voto. Fica no disco. Não há importador. |
| `log.jez` | Log da urna. Fica no disco. |
| `vota.vsc` | Arquivo auxiliar da urna. Fica no disco. |

A ausência de `imgbu.dat` deixa o relatório de poder inteiro. A ausência de `bu.dat` deixa aquela seção fora dos totais.

## Ler os códigos de saída

| Código | Significado |
| --- | --- |
| `0` | A etapa terminou. |
| `1` | Falha de rede, de disco, de leitura ou de banco. |
| `2` | A eleição ou o turno não está publicado, ou não havia arquivo para importar. |

## Seguir a sequência de 2026

1. Copie `.env.example` para `.env` e confirme `ANO_ELEICAO=2026`.
2. Suba o banco com `make up`.
3. Baixe os zips com `uv run python -m eleicoes download --ano 2026`.
4. Importe as correspondências com `uv run python -m eleicoes import --ano 2026 --origem downloads/2026`.
5. Baixe as urnas com `uv run python scripts/manter_urnas_2026.py`.
6. Para cada UF com `fim UF saída=0` no `resumo.log`, importe os boletins. Inclua `ZZ` no presidente nacional.
7. Liste as ausências com `uv run python -m eleicoes ausentes --ano 2026 --turno 1`.
8. Abra o relatório com `uv run python scripts/relatorio_poder.py --ano 2026 --turno 1 --cargo presidente`.
9. Depois de uma importação nova, rode o mesmo relatório com `--atualizar`.
10. Cruze presidente e governador com `uv run python scripts/relatorio_presidente_governador.py --ano 2026 --turno 1`. Depois de uma importação nova, rode o mesmo comando com `--atualizar`.
