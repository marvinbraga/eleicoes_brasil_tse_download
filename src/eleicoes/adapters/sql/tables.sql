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
