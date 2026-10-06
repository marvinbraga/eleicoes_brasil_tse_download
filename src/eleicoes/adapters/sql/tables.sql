CREATE SCHEMA IF NOT EXISTS raw;

CREATE SCHEMA IF NOT EXISTS analise;

CREATE TABLE IF NOT EXISTS raw.csec (
    dt_geracao text,
    hh_geracao text,
    aa_eleicao text,
    cd_pleito text,
    sg_uf text,
    cd_municipio text,
    nm_municipio text,
    nr_zona text,
    nr_secao text,
    nr_local_votacao text,
    nr_urna_esperada text,
    cd_carga_urna_esperada text,
    cd_flashcard_urna_esperada text,
    dt_carga_urna_esperada text,
    st_corresp_alterada text,
    nm_maquina_geracao_midia text,
    nr_sri_tpm_geracao_midia text,
    nr_sri_instal_geracao_midia text,
    nm_maquina_transm_corresp text,
    nr_sri_tpm_transm_corresp text,
    nr_sri_instal_transm_corresp text,
    arquivo text NOT NULL,
    membro text NOT NULL,
    geracao text NOT NULL
);

CREATE INDEX IF NOT EXISTS csec_arquivo_membro_idx ON raw.csec (arquivo, membro);

CREATE TABLE IF NOT EXISTS raw.ccont (
    dt_geracao text,
    hh_geracao text,
    aa_eleicao text,
    cd_pleito text,
    sg_uf text,
    cd_municipio text,
    nm_municipio text,
    nr_zona text,
    nr_urna_esperada text,
    cd_carga_urna_esperada text,
    cd_flashcard_urna_esperada text,
    dt_carga_urna_esperada text,
    st_corresp_alterada text,
    nm_maquina_geracao_midia text,
    nr_sri_tpm_geracao_midia text,
    nr_sri_instal_geracao_midia text,
    nm_maquina_transm_corresp text,
    nr_sri_tpm_transm_corresp text,
    nr_sri_instal_transm_corresp text,
    arquivo text NOT NULL,
    membro text NOT NULL,
    geracao text NOT NULL
);

CREATE INDEX IF NOT EXISTS ccont_arquivo_membro_idx ON raw.ccont (arquivo, membro);

CREATE TABLE IF NOT EXISTS raw.carga (
    conjunto text NOT NULL,
    turno text NOT NULL,
    uf text NOT NULL,
    arquivo text NOT NULL,
    membro text NOT NULL,
    tabela text NOT NULL,
    geracao text NOT NULL,
    linhas bigint NOT NULL,
    situacao text NOT NULL,
    carregado_em timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS carga_arquivo_membro_idx ON raw.carga (arquivo, membro);

CREATE TABLE IF NOT EXISTS raw.boletim (
    ano integer NOT NULL,
    turno integer NOT NULL,
    uf text NOT NULL,
    municipio integer NOT NULL,
    zona integer NOT NULL,
    secao integer NOT NULL,
    local integer NOT NULL,
    arquivo text NOT NULL,
    id_eleicao integer NOT NULL,
    eleitores_aptos integer NOT NULL,
    qtd_comparecimento integer NOT NULL,
    eleitores_complemento integer NOT NULL,
    eleitores_computados integer NOT NULL,
    indicador_habilitacao integer NOT NULL,
    qtd_biometria integer NOT NULL,
    qtd_manual integer NOT NULL,
    tipo_cargo text NOT NULL,
    cargo text NOT NULL,
    ordem_impressao integer NOT NULL,
    comparecimento_cargo integer NOT NULL,
    tipo_voto text NOT NULL,
    partido integer,
    numero integer,
    quantidade integer NOT NULL,
    numero_interno_urna integer NOT NULL,
    codigo_carga text NOT NULL,
    codigo_midia text NOT NULL,
    data_hora_emissao text NOT NULL,
    data_hora_carga text NOT NULL
);

-- Null partido and numero use a sentinel so branco and nulo stay unique.
CREATE UNIQUE INDEX IF NOT EXISTS boletim_voto_uidx ON raw.boletim (
    ano,
    turno,
    uf,
    municipio,
    zona,
    secao,
    id_eleicao,
    cargo,
    tipo_voto,
    (COALESCE(partido, -1)),
    (COALESCE(numero, -1))
);

CREATE INDEX IF NOT EXISTS boletim_uf_cargo_numero_idx ON raw.boletim (uf, cargo, numero);

CREATE INDEX IF NOT EXISTS boletim_secao_idx ON raw.boletim (uf, municipio, zona, secao);
