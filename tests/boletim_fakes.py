"""Boletins válidos para testes que não abrem arquivo nem banco."""

from eleicoes.domain.boletim import Boletim, VoteLine


def nominal_line(
    *,
    id_eleicao: int = 6257,
    eleitores_aptos: int = 277,
    qtd_comparecimento: int = 277,
    qtd_eleitores_complemento: int = 0,
    tipo_cargo: str = "majoritario",
    cargo: str = "presidente",
    ordem_impressao: int = 5,
    comparecimento_cargo: int = 1,
    tipo_voto: str = "nominal",
    partido: int | None = 13,
    numero: int | None = 13,
    quantidade: int = 1,
) -> VoteLine:
    return VoteLine(
        id_eleicao=id_eleicao,
        eleitores_aptos=eleitores_aptos,
        qtd_comparecimento=qtd_comparecimento,
        qtd_eleitores_complemento=qtd_eleitores_complemento,
        tipo_cargo=tipo_cargo,
        cargo=cargo,
        ordem_impressao=ordem_impressao,
        comparecimento_cargo=comparecimento_cargo,
        tipo_voto=tipo_voto,
        partido=partido,
        numero=numero,
        quantidade=quantidade,
    )


def bulletin(
    arquivo: str = "01104/0005/0028/a-bu.dat",
    *,
    secao: int = 28,
    votos: tuple[VoteLine, ...] | None = None,
) -> Boletim:
    return Boletim(
        arquivo=arquivo,
        fase="oficial",
        municipio=1104,
        zona=5,
        local=1023,
        secao=secao,
        data_hora_emissao="20261004T155025",
        versao_urna="10.23.0.0",
        numero_interno_urna=2295748,
        data_hora_carga="20260924T085600",
        codigo_carga="136568155446399692414911",
        codigo_midia="ZAC001STD29",
        eleitores_computados=1,
        indicador_habilitacao=1,
        qtd_biometria=1,
        qtd_manual=0,
        votos=(nominal_line(),) if votos is None else votos,
    )
