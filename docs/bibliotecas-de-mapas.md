# Mapas de presidente e governador

Você gera um único HTML estático que desenha o partido líder em cada recorte. Este texto fixa o que entra nesse arquivo: o OpenLayers, o conversor de TopoJSON e as malhas que o mapa desenha. Os tamanhos e os endereços abaixo foram medidos em 8 de outubro de 2026. Você não troca versão, tamanho, licença nem URL por um valor que não esteja aqui.

O mesmo desenho vale para o relatório de presidente e para o de governador. O que muda de um relatório para o outro é o resultado que o Python já calculou antes de escrever o HTML.

## Requisitos do produto

Estes itens são requisitos do produto. Não são achados de documentação de biblioteca.

- O zoom mínimo mostra o resultado do país.
- Os zooms intermediários mostram as regiões e, em seguida, os estados.
- O zoom máximo mostra os municípios.
- Cada área mostra três coisas do partido líder daquele recorte: o resultado numérico, a logomarca do partido e o polígono preenchido com a cor do partido.
- Número, logomarca e cor aparecem em todo nível de zoom.
- A página é um único arquivo HTML que o Python gera.
- O arquivo abre offline, a partir do disco, sem chave e sem rede.
- Você não usa React, Vite nem um build Node.
- Você não usa Matplotlib, GeoPandas nem Shapely.
- A malha entra como GeoJSON ou TopoJSON, e o JavaScript e a malha cabem dentro do HTML gerado.

## Bibliotecas que você embute

Você usa duas bibliotecas no mapa. O OpenLayers desenha. O topojson-client só converte a malha. Nenhuma das duas traz o contorno do Brasil.

O OpenLayers 10.11.0 é o único renderizador. A licença SPDX é BSD-2-Clause. O npm publicou essa versão em 4 de outubro de 2026. O script `dist/ol.js` mede 1.070.771 bytes crus e 297.882 bytes em gzip. O `ol.css` mede 6.343 bytes crus e 1.466 bytes em gzip. Esse gzip é `gzip -9` dos bytes baixados do unpkg naquela data. O número é o peso no navegador, não o tamanho descompactado do pacote no npm.

Você baixa o OpenLayers nestes endereços:

- Script: [https://unpkg.com/ol@10.11.0/dist/ol.js](https://unpkg.com/ol@10.11.0/dist/ol.js)
- CSS: [https://unpkg.com/ol@10.11.0/ol.css](https://unpkg.com/ol@10.11.0/ol.css)
- Registro: [https://registry.npmjs.org/ol](https://registry.npmjs.org/ol)

O CSS medido não fica em `dist/`. No unpkg ele está na raiz do pacote, no endereço acima.

O topojson-client 3.1.0 transforma TopoJSON em GeoJSON antes de o OpenLayers ler a malha. A licença SPDX é ISC. O npm publicou essa versão em 6 de novembro de 2019, e ela ainda é a `latest`. O arquivo `dist/topojson-client.min.js` mede 7.169 bytes crus e 2.605 bytes em gzip, no mesmo critério de 8 de outubro de 2026. O pacote está velho. A idade é falta de versão nova, não um formato quebrado. A descrição publicada do pacote é manipular TopoJSON e convertê-lo em GeoJSON.

Você baixa o conversor nestes endereços:

- Script: [https://unpkg.com/topojson-client@3.1.0/dist/topojson-client.min.js](https://unpkg.com/topojson-client@3.1.0/dist/topojson-client.min.js)
- Registro: [https://registry.npmjs.org/topojson-client](https://registry.npmjs.org/topojson-client)

O formato TopoJSON do próprio OpenLayers não foi verificado. Você não chama um leitor TopoJSON do OpenLayers. A conversão acontece antes, no topojson-client.

## Como você embute o OpenLayers

Você cola o texto de `ol.js` e de `ol.css` dentro do HTML. O script é clássico. O arquivo começa com `var ol=`. O global da página é `ol`. Você não usa `<script type="module">`.

Os exemplos atuais do site são módulos ESM montados com Vite. Esse não é o caminho deste relatório. Você não copia esses `import`. Você cola o `dist/ol.js` da 10.11.0.

Não há chave de API nessa trilha. Não há servidor de tiles. Não há worker. O exemplo de rótulos que você segue monta o mapa com uma camada vetorial, fundo branco, um GeoJSON local e nenhuma tile. Você não adiciona uma camada de ruas.

A licença BSD-2-Clause permite redistribuir o binário se o aviso de copyright, as condições e o aviso de isenção de responsabilidade forem junto. Você cola esses avisos no HTML. Você cola também o aviso ISC do topojson-client.

A documentação que a pesquisa abriu, e que você usa como contrato, está aqui:

- Camada 10.11.0, onde estão `minZoom` e `maxZoom`: [Layer](https://openlayers.org/en/v10.11.0/apidoc/module-ol_layer_Layer-Layer.html)
- `Icon` 10.11.0: [Icon](https://openlayers.org/en/v10.11.0/apidoc/module-ol_style_Icon-Icon.html)
- Rótulo e `declutter`: [exemplo de declutter](https://openlayers.org/en/latest/examples/vector-label-decluttering.html)
- Leitor de GeoJSON, página da 10.1.0, que é a página aberta na pesquisa: [GeoJSON](https://openlayers.org/en/v10.1.0/apidoc/module-ol_format_GeoJSON-GeoJSON.html)

A página do GeoJSON não foi reaberta para a 10.11.0. O que ela documenta, e o que você aplica, é a projeção de dados EPSG:4326.

## Como cada zoom desenha a área

Você cria uma camada vetorial por recorte. A camada do país fica no zoom mínimo. A das regiões e a dos estados ficam nos patamares do meio, nesta ordem: primeiro as regiões, depois os estados. A dos municípios fica só no zoom máximo. O mundo fica em segundo plano e não recebe resultado eleitoral.

A opção documentada trata `minZoom` como exclusivo e `maxZoom` como inclusivo. Os setters descrevem o inverso. O mecanismo de esconder o recorte errado já está na camada, sem plugin. No primeiro HTML você fixa os quatro limiares e confere na tela em que zoom cada camada aparece e some. Esta pesquisa não mediu esses números de zoom. Você não copia um limiar de outra biblioteca.

O estilo lê propriedades que o Python gravou na feição. A cor do partido não é uma escala contínua. A função de estilo lê a cor do líder daquele recorte e devolve o `Fill`. O resultado numérico vai no `Text` do mesmo estilo. A logomarca vai na classe `Icon`.

O construtor documentado do `Icon` recebe `src` como URI da imagem e aceita `declutterMode`. Você embute poucas imagens, uma por partido, como data URI. Cada feição aponta para a URI do seu líder. Você não gera uma imagem nova por município.

O exemplo publicado de polígonos demonstra o texto, não o ícone. O ícone não senta no anel do polígono. Você ancora o ícone no centróide do IBGE, em longitude e latitude. Esse ponto existe na malha municipal da seção seguinte. Nas outras malhas, você só usa um centróide que o arquivo realmente traga. Você não inventa o ponto.

O requisito pede a logomarca em toda área. Com `declutter: true`, cidades muito próximas no zoom máximo perdem o rótulo em vez de formar um monte ilegível. Essa omissão não cumpre o requisito onde os retângulos se cruzam. A mesma camada aceita `declutter: false` e mantém todas as marcas. A pesquisa não mediu quantas logomarcas cabem na tela de uma região metropolitana. Você confere esse zoom no primeiro HTML. Você não trata a omissão como se ela satisfizesse o requisito.

O leitor de GeoJSON usa EPSG:4326 como projeção dos dados. Os exemplos de vista chamam `fromLonLat`. As coordenadas medidas na malha de UF estão em graus decimais, então você reprojeta as feições para a vista. Não há chave nessa etapa. No script global você chama o `fromLonLat` que o `ol.js` publica. Você não usa o import ESM.

Os 5.570 polígonos municipais não são o precipício que o tamanho sugere, desde que a malha seja a simplificada. Balla e Gede, no ISPRS International Journal of Geo-Information de 2025, mediram tempo de primeiro desenho, não taxa de quadros. Leaflet e OpenLayers foram os mais rápidos até 10.000 polígonos. Em 50.000 polígonos o OpenLayers ficou em 1.366,4 ms, com desvio-padrão de 11,42 ms no PDF. O estudo não usou a malha do IBGE e não separou vértices de feições. O PDF está em [https://www.mdpi.com/2220-9964/14/9/336/pdf?version=1756544202](https://www.mdpi.com/2220-9964/14/9/336/pdf?version=1756544202). Ninguém publicou taxa de quadros para os municípios brasileiros.

Se o deslocamento pesar, a mesma biblioteca documenta `RenderFeature` para feições que ninguém vai editar. Há um exemplo que fatia o GeoJSON em vector tiles no navegador, sem servidor: [geojson-vt](https://openlayers.org/en/latest/examples/geojson-vt.html). Esse exemplo puxa outro pacote, que este mapa não adota agora.

## Como você converte TopoJSON em GeoJSON

O OpenLayers deste relatório lê GeoJSON. O Python pode colar o TopoJSON no HTML, ou colar o GeoJSON já convertido. Se o que chega ao navegador ainda é TopoJSON, a página roda o topojson-client e só então entrega o GeoJSON ao formato do OpenLayers.

O objeto de países em `countries-110m.json` se chama `countries`. Há também um objeto `land`, com uma geometria, que o mapa não desenha. O TopoJSON municipal da API v3, que você não usa como malha dos municípios, nomeia o objeto `BRMU`. Medido em 13 de outubro de 2026, a malha municipal v2 tem um único objeto, chamado `foo`, e a malha de UF v3 tem um único objeto, chamado `BRUF`, sem centróide. Você lê a chave `objects` do arquivo que baixou e confere com esses nomes. Você não inventa outro.

## Malhas que o mapa desenha

Você embute os quatro recortes da tabela. As cinco regiões ficam de fora desta tabela de propósito: não foram medidas, e você não inventa arquivo, tamanho, contagem nem URL para elas.

O crédito ao IBGE é obrigatório. O crédito à Natural Earth não é necessário. A licença ISC do `world-atlas` cobre o código do pacote, não a geometria.

| Recorte | Arquivo | Tamanho medido | Feições | Licença | Chave de junção |
| --- | --- | --- | --- | --- | --- |
| Municípios | TopoJSON do IBGE, API v2, `resolucao=5`, `qualidade=1` | 1.626.114 bytes | 5.570 | CC BY 4.0 na nota de 2024 da malha, com crédito ao IBGE | `codarea` de 7 dígitos, mais `centroide` |
| UFs | TopoJSON do IBGE, API v3, `intrarregiao=UF`, `qualidade=minima` | 31.464 bytes | 27 | A mesma nota, por ser malha do IBGE | `codarea` de 2 dígitos |
| País | A feição do Brasil dentro de `countries-110m.json` | 107.761 bytes, o arquivo inteiro; a feição do Brasil não foi medida à parte | 1 feição de resultado, dentro do arquivo de 177 | Domínio público na geometria da Natural Earth; ISC só no código do pacote | `id` numérico do ISO 3166-1 |
| Mundo | `world-atlas` 2.0.2, `countries-110m.json` | 107.761 bytes | 177 | A mesma da linha de país | `id` numérico do ISO 3166-1, não o alpha-2 |

### Municípios

O arquivo que você embute, medido em 8 de outubro de 2026, é este:

[https://servicodados.ibge.gov.br/api/v2/malhas/BR?resolucao=5&qualidade=1&formato=application/json](https://servicodados.ibge.gov.br/api/v2/malhas/BR?resolucao=5&qualidade=1&formato=application/json)

Nessa API, `formato=application/json` é TopoJSON. O arquivo tem 5.570 geometrias. Cada `codarea` tem 7 dígitos. A amostra lida é Alta Floresta D'Oeste, `1100015`, com `centroide` em longitude e latitude. A malha inclui Fernando de Noronha, `2605459`. A malha não inclui Boa Esperança do Norte, código IBGE `5101837`.

Você fica na v2 com `qualidade=1` porque o centróide está nesse arquivo e a logo precisa desse ponto. A v3 com `qualidade=minima` é menor, 1.428.796 bytes, e repete os mesmos 5.570 códigos, mas o centróide não foi visto nesse arquivo. Você não troca para a v3 para economizar bytes. O endereço dela, só para não confundi-lo com a malha adotada, é [https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?intrarregiao=municipio&qualidade=minima&formato=application/json](https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?intrarregiao=municipio&qualidade=minima&formato=application/json). A v2 com `qualidade=3` sobe a 2.116.662 bytes e não é o arquivo deste mapa.

A nota jurídica de 2024 diz que a Malha Municipal Digital e os produtos derivados saem em licença compatível com CC BY 4.0. Você pode distribuir e adaptar, inclusive para uso comercial, desde que credite o IBGE. O PDF é [liv102169.pdf](https://biblioteca.ibge.gov.br/visualizacao/livros/liv102169.pdf). Essa frase foi lida para a malha de 2024. Não foi reaberta para o zip de 2025. O JSON da API não mostrou um campo de licença. Você mantém o crédito ao IBGE no HTML mesmo assim.

O shapefile oficial não entra no HTML. `BR_Municipios_2024.zip` tem 208.153.231 bytes e o de 2025 tem 237.062.431 bytes, na listagem do [GeoFTP de malhas municipais](https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/). A base de 2024 está na escala 1:250.000, em SIRGAS 2000. Nenhum municipal medido ficou abaixo de 1 MB.

### Estados

O TopoJSON das 27 UFs, Distrito Federal incluído, mede 31.464 bytes na API v3 com `qualidade=minima`. A pesquisa cola na íntegra o endereço do GeoJSON irmão, de 98.502 bytes e 27 feições:

[https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?intrarregiao=UF&qualidade=minima&formato=application/vnd.geo+json](https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?intrarregiao=UF&qualidade=minima&formato=application/vnd.geo+json)

O TopoJSON de 31.464 bytes é o mesmo serviço, com `formato=application/json`, que a nota define como TopoJSON. Você confere o tamanho ao baixar. Os `codarea` lidos no GeoJSON são `11`, `12`, `13`, `14`, `15`, `16`, `17`, `21`, `22`, `23`, `24`, `25`, `26`, `27`, `28`, `29`, `31`, `32`, `33`, `35`, `41`, `42`, `43`, `50`, `51`, `52` e `53`. As coordenadas estão em graus decimais. Uma amostra fica perto de −62 e −13.

O GeoJSON em qualidade máxima chega a 1.001.279 bytes e não vale o peso de um coroplético. O GeoJSON intermediário mede 251.135 bytes. Você embute o TopoJSON mínimo.

Você não pinta a UF pelo código de UF do TSE. A malha usa o `codarea` de dois dígitos do IBGE. A ponte está na seção do cruzamento.

### País e mundo

O polígono do zoom mínimo é uma feição: o Brasil dentro de `countries-110m.json`. Você não fabrica esse polígono pela união das UFs.

O arquivo é o `world-atlas` 2.0.2, neste endereço do jsDelivr:

[https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json](https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json)

O registro do pacote é [https://registry.npmjs.org/world-atlas/latest](https://registry.npmjs.org/world-atlas/latest). O repositório descreve a 2.0.2 como redistribuição da Natural Earth 4.1.0 em TopoJSON, em graus decimais: [topojson/world-atlas](https://github.com/topojson/world-atlas). A geometria é de domínio público. Os termos estão em [https://www.naturalearthdata.com/about/terms-of-use/](https://www.naturalearthdata.com/about/terms-of-use/). O uso, a alteração e a redistribuição não pedem permissão nem crédito. A licença ISC vale para o código do pacote, não para esse JSON. Você não precisa colar o código do pacote para embutir a geometria.

O arquivo mede 107.761 bytes. A topologia tem o objeto `countries`, com 177 geometrias, e o objeto `land`, com uma. O `id` é o ISO 3166-1 numérico. Não há alpha-2. A feição que a pesquisa leu é `"242"`, Fiji. A pesquisa não abriu a linha do Brasil. O README fixa o `id` nesse código numérico, e a nota de junção aponta `076` para o Brasil quando a chave é o ISO numérico de três dígitos. Você seleciona o Brasil por essa regra e confere o `id` no arquivo antes de pintar. 177 países não são a lista ISO completa. O arquivo serve de fundo e de contorno do país. Não serve de cadastro ISO completo.

O `countries-50m.json` mede 756.420 bytes em [https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-50m.json](https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-50m.json). Este mapa não o embute. O fundo e o zoom mínimo usam o de 110m.

O zip oficial da Natural Earth em 1:110 milhões não entra no HTML. Ele está em [https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip](https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip) e mede 214.976 bytes. Você usa o TopoJSON do `world-atlas`.

Você desenha os outros países como fundo, sem cor de partido, sem número e sem logomarca. O resultado do zoom mínimo fica só na feição do Brasil.

### Regiões, um município e o exterior

As cinco regiões são requisito do zoom intermediário e não foram baixadas. Não há tamanho, contagem nem URL conferida para esse recorte. Você não inventa o parâmetro da API. A página de documentação, sem tratar parâmetro algum como já medido, é [https://servicodados.ibge.gov.br/api/docs/malhas?versao=3](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3). Até esse arquivo ser baixado e medido, a camada de regiões não tem geometria para mostrar.

Boa Esperança do Norte, em Mato Grosso, está na tabela do TSE com código IBGE `5101837` e código TSE `73709`. A malha da API não tem `5101837`. Esse município fica sem polígono. O zip municipal de 2025 não foi aberto, então você não assume que ele contém essa cidade. O zoom máximo desenha as 5.570 cidades da malha simplificada, não as 5.571 linhas do cadastro de 4 de outubro de 2026.

A UF `ZZ` é o exterior. Ela não tem polígono. O mapa-múndi não localiza esse voto. Você não inventa um contorno de consulado.

## Cruzamento entre TSE e IBGE

A malha e o resultado do TSE não se encontram por igualdade de texto. O IBGE identifica o município com 7 dígitos no `codarea`. Os dois primeiros são a UF. O TSE usa um código de município de 5 dígitos e outro código de UF. Em todas as linhas da tabela oficial, os dois códigos de município diferem e os dois códigos de UF diferem.

A ponte é `municipio_tse_ibge.csv`, dentro deste zip:

[https://cdn.tse.jus.br/estatistica/sead/odsele/municipio_tse_ibge/municipio_tse_ibge.zip](https://cdn.tse.jus.br/estatistica/sead/odsele/municipio_tse_ibge/municipio_tse_ibge.zip)

A ficha no portal de dados abertos está em [https://dadosabertos.tse.jus.br/dataset/codigos-oficiais-de-uf-e-municipios-segundo-o-tse-e-o-ibge](https://dadosabertos.tse.jus.br/dataset/codigos-oficiais-de-uf-e-municipios-segundo-o-tse-e-o-ibge).

O zip mediu 139.020 bytes em 4 de outubro de 2026, com carimbo interno `04/10/2026` `09:00:06`. Remediado em 13 de outubro de 2026, o mesmo URL mede 139.031 bytes, com `Last-Modified` de 11 de outubro de 2026 e carimbo interno `11/10/2026` `09:00:16`. O CSV interno continua com 520.088 bytes. O dono aceitou, nessa data, a trava de 139.031 bytes condicionada a esse CSV. A codificação é latin-1 e o separador é ponto e vírgula. Há 5.571 linhas de dados. O cabeçalho é `DT_GERACAO`, `HH_GERACAO`, `CD_UF_TSE`, `CD_UF_IBGE`, `SG_UF`, `NM_UF`, `CD_MUNICIPIO_TSE`, `NM_MUNICIPIO_TSE`, `CD_MUNICIPIO_IBGE` e `NM_MUNICIPIO_IBGE`.

Todos os 5.571 valores de `CD_MUNICIPIO_IBGE` têm 7 dígitos e são únicos. Todos os 5.571 valores de `CD_MUNICIPIO_TSE` têm 5 dígitos e são únicos. `SG_UF` tem 27 valores, os 26 estados e o Distrito Federal, e não tem `ZZ`. `CD_UF_IBGE` tem sempre 2 dígitos. `CD_UF_TSE` tem 1 dígito em 3.567 linhas e 2 dígitos em 2.004 linhas.

São Paulo é `SG_UF` SP, `CD_UF_TSE` 1, `CD_UF_IBGE` 35, `CD_MUNICIPIO_TSE` `71072` e `CD_MUNICIPIO_IBGE` `3550308`. Brasília é `CD_UF_TSE` 20, `CD_UF_IBGE` 53, TSE `97012` e IBGE `5300108`.

Você não corta nem completa com zero o código de 7 dígitos para compará-lo ao de 5. Você não pinta a UF pelo `CD_UF_TSE`. A chave da malha de UF é `CD_UF_IBGE`, ou a sigla em `SG_UF` quando o recorte já está agregado por sigla. Bujari, no Acre, ilustra o zero à esquerda: o TSE vem como `01007`, entre aspas no CSV, e o IBGE é `1200138`. Você lê o arquivo sem perder esse zero.

O caminho da junção municipal é este. Você parte do código TSE de 5 dígitos, acha a linha no CSV, lê `CD_MUNICIPIO_IBGE` e casa com o `codarea` da malha. O campo `cdi` da especificação de divulgação é descrito como cinco dígitos “segundo o IBGE”. Não é o `codarea`. Você não o usa como chave até inspecionar um JSON real de divulgação.

O `leiame.pdf` do zip mede 60.546 bytes e não foi lido. A licença de redistribuição da tabela não está estabelecida. O arquivo é público, e isso não é o mesmo que uma licença citada. Você usa a tabela ao gerar o HTML. Você não trata este documento como autorização para redistribuir o CSV.

Fernando de Noronha está nos dois lados: TSE `30015` e IBGE `2605459`, e a malha tem o polígono. Boa Esperança do Norte está só na tabela. O cruzamento inteiro acontece no Python, na hora de gerar o HTML. O navegador não redescobre o código eleitoral.

## Propriedades que o Python grava

Antes de o navegador abrir, cada feição de resultado já traz nas `properties` o que o estilo vai ler. Os nomes dos campos são os que o seu estilo consultar. Os quatro valores não podem faltar.

- A cor do partido líder daquele recorte, lida pelo `Fill`.
- O resultado numérico daquele recorte, lido pelo `Text`.
- A data URI da logomarca desse partido, usada como `src` do `Icon`.
- O código que encaixou a feição na malha. No município são os 7 dígitos do IBGE. Na UF são os 2 dígitos do `codarea`. No país não há `codarea`: a feição do Brasil guarda o `id` numérico que a selecionou.

Você grava a chave já resolvida. Cor, número e logo são do partido líder da área, em todo zoom que tenha geometria. Presidente e governador usam as mesmas quatro propriedades e a mesma pilha de camadas.

A página credita o IBGE. A página leva os avisos BSD-2-Clause do OpenLayers e o aviso ISC do topojson-client. A geometria da Natural Earth não pede crédito.

No primeiro HTML você ainda confere cinco coisas. O arquivo abre do disco, sem servidor e sem pedido de rede. O global é `ol`, sem import ESM. Os quatro cortes de zoom aparecem e somem no limiar, com a ressalva inclusiva ou exclusiva já descrita. A logo municipal senta no centróide. Boa Esperança do Norte, a UF `ZZ` e as cinco regiões ficam sem polígono inventado.

## Reserva

Leaflet 1.9.4 e MapLibre GL JS 6.13.0 ficam só como reserva, e não são o que você implementa agora. O Leaflet perde porque a logomarca, nessa versão, é um `DivIcon` em HTML e a biblioteca não tem declutter, então as marcas das áreas passam a ser código seu. O MapLibre GL JS 6.13.0 perde porque o worker da versão 6 não sobe quando a página abre em `file://`, e este relatório é um arquivo aberto do disco.
