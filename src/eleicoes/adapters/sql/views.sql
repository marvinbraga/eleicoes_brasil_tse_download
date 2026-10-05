CREATE OR REPLACE VIEW analise.secao AS
SELECT DISTINCT ON (c.sg_uf, c.cd_municipio, c.nr_zona, c.nr_secao)
    to_timestamp(c.geracao, 'DDMMYYYYHH24MI') AS geracao_em,
    c.arquivo,
    c.membro,
    to_date(c.dt_geracao, 'DD/MM/YYYY') AS dt_geracao,
    c.hh_geracao::time AS hh_geracao,
    c.aa_eleicao::integer AS aa_eleicao,
    c.cd_pleito,
    c.sg_uf,
    c.cd_municipio,
    c.nm_municipio,
    c.nr_zona::integer AS nr_zona,
    c.nr_secao::integer AS nr_secao,
    c.nr_local_votacao,
    c.nr_urna_esperada,
    c.cd_carga_urna_esperada,
    c.cd_flashcard_urna_esperada,
    c.dt_carga_urna_esperada::timestamp AS dt_carga_urna_esperada,
    (c.st_corresp_alterada = 'S') AS alterada,
    c.nm_maquina_geracao_midia,
    c.nr_sri_tpm_geracao_midia,
    c.nr_sri_instal_geracao_midia,
    c.nm_maquina_transm_corresp,
    c.nr_sri_tpm_transm_corresp,
    c.nr_sri_instal_transm_corresp
FROM raw.csec AS c
ORDER BY c.sg_uf, c.cd_municipio, c.nr_zona, c.nr_secao,
    to_timestamp(c.geracao, 'DDMMYYYYHH24MI') DESC;

CREATE OR REPLACE VIEW analise.contingencia AS
SELECT DISTINCT ON (c.sg_uf, c.cd_municipio, c.nr_zona, c.nr_urna_esperada)
    to_timestamp(c.geracao, 'DDMMYYYYHH24MI') AS geracao_em,
    c.arquivo,
    c.membro,
    to_date(c.dt_geracao, 'DD/MM/YYYY') AS dt_geracao,
    c.hh_geracao::time AS hh_geracao,
    c.aa_eleicao::integer AS aa_eleicao,
    c.cd_pleito,
    c.sg_uf,
    c.cd_municipio,
    c.nm_municipio,
    c.nr_zona::integer AS nr_zona,
    c.nr_urna_esperada,
    c.cd_carga_urna_esperada,
    c.cd_flashcard_urna_esperada,
    c.dt_carga_urna_esperada::timestamp AS dt_carga_urna_esperada,
    (c.st_corresp_alterada = 'S') AS alterada,
    c.nm_maquina_geracao_midia,
    c.nr_sri_tpm_geracao_midia,
    c.nr_sri_instal_geracao_midia,
    c.nm_maquina_transm_corresp,
    c.nr_sri_tpm_transm_corresp,
    c.nr_sri_instal_transm_corresp
FROM raw.ccont AS c
ORDER BY c.sg_uf, c.cd_municipio, c.nr_zona, c.nr_urna_esperada,
    to_timestamp(c.geracao, 'DDMMYYYYHH24MI') DESC;

CREATE OR REPLACE VIEW analise.resumo_uf AS
SELECT
    sg_uf,
    count(*) AS secoes,
    count(DISTINCT cd_municipio) AS municipios,
    count(*) FILTER (WHERE alterada) AS secoes_alteradas,
    max(geracao_em) AS geracao_em
FROM analise.secao
GROUP BY sg_uf;

CREATE OR REPLACE VIEW analise.resumo_contingencia_uf AS
SELECT
    sg_uf,
    count(*) AS urnas,
    count(DISTINCT cd_municipio) AS municipios,
    count(*) FILTER (WHERE alterada) AS urnas_alteradas,
    max(geracao_em) AS geracao_em
FROM analise.contingencia
GROUP BY sg_uf;

CREATE OR REPLACE VIEW analise.alteradas AS
SELECT
    'secao'::text AS tipo,
    sg_uf,
    cd_municipio,
    nm_municipio,
    nr_zona,
    nr_secao,
    nr_urna_esperada,
    geracao_em,
    arquivo
FROM analise.secao
WHERE alterada
UNION ALL
SELECT
    'contingencia'::text,
    sg_uf,
    cd_municipio,
    nm_municipio,
    nr_zona,
    NULL::integer,
    nr_urna_esperada,
    geracao_em,
    arquivo
FROM analise.contingencia
WHERE alterada;

CREATE OR REPLACE VIEW analise.cargas AS
SELECT
    conjunto,
    turno,
    uf,
    arquivo,
    membro,
    tabela,
    geracao,
    CASE
        WHEN geracao ~ '^[0-9]{12}$' THEN to_timestamp(geracao, 'DDMMYYYYHH24MI')
        ELSE NULL
    END AS geracao_em,
    linhas,
    situacao,
    carregado_em
FROM raw.carga;
