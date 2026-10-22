"""JSON of the seat estimate. The scoreboard (placar) reads `partidos`."""

from fractions import Fraction
from typing import Final, Self

from pydantic import BaseModel

from eleicoes.domain.federacoes import RegistroPartidario
from eleicoes.domain.majoritario import ResultadoGoverno, ResultadoSenado, VotoCandidato
from eleicoes.domain.percentual import format_percent
from eleicoes.domain.proporcional import Eleito, ResultadoLista
from eleicoes.domain.simulacao_cadeiras import (
    CASA_CAMARA,
    NOTAS,
    CasaSimulada,
    CasaUf,
    ForcaPartido,
    SimulacaoCadeiras,
)
from eleicoes.use_cases.simular_cadeiras import SimulacaoGravada

_NOMES_CASA: Final = {CASA_CAMARA: "Câmara dos Deputados"}
_ASSEMBLEIAS: Final = "Assembleias Legislativas e Câmara Legislativa do DF"


class LegendaJson(BaseModel):
    codigo: str
    sigla: str
    nome: str
    federacao: bool
    partidos: list[int]


class ListaJson(BaseModel):
    legenda: str
    votos: int
    votos_legenda: int
    quociente_partidario: int
    cadeiras_quociente: int
    cadeiras_media: int
    cadeiras_media_livre: int
    cadeiras: int

    @classmethod
    def from_domain(cls, item: ResultadoLista) -> Self:
        return cls(
            legenda=item.legenda,
            votos=item.votos,
            votos_legenda=item.votos_legenda,
            quociente_partidario=item.quociente_partidario,
            cadeiras_quociente=item.cadeiras_quociente,
            cadeiras_media=item.cadeiras_media,
            cadeiras_media_livre=item.cadeiras_media_livre,
            cadeiras=item.cadeiras,
        )


class EleitoJson(BaseModel):
    numero: int
    partido: int
    legenda: str
    votos: int
    fase: str
    empate: bool

    @classmethod
    def from_domain(cls, item: Eleito) -> Self:
        return cls(
            numero=item.numero,
            partido=item.partido,
            legenda=item.legenda,
            votos=item.votos,
            fase=item.fase,
            empate=item.empate,
        )


class CasaUfJson(BaseModel):
    uf: str
    cargo: str
    vagas: int
    votos_validos: int
    quociente_eleitoral: int
    vagas_sem_candidato: int
    listas: list[ListaJson]
    eleitos: list[EleitoJson]

    @classmethod
    def from_domain(cls, item: CasaUf) -> Self:
        resultado = item.resultado
        return cls(
            uf=item.uf,
            cargo=item.cargo,
            vagas=resultado.vagas,
            votos_validos=resultado.votos_validos,
            quociente_eleitoral=resultado.quociente_eleitoral,
            vagas_sem_candidato=resultado.vagas_sem_candidato,
            listas=[ListaJson.from_domain(lista) for lista in resultado.listas if lista.votos],
            eleitos=[EleitoJson.from_domain(eleito) for eleito in resultado.eleitos],
        )


class LegendaCadeirasJson(BaseModel):
    legenda: str
    cadeiras: int


class PartidoCadeirasJson(BaseModel):
    partido: int
    cadeiras: int


class CasaJson(BaseModel):
    casa: str
    nome: str
    vagas: int
    vagas_simuladas: int
    ufs_sem_votos: list[str]
    legendas: list[LegendaCadeirasJson]
    partidos: list[PartidoCadeirasJson]
    ufs: list[CasaUfJson]

    @classmethod
    def from_domain(cls, casa: CasaSimulada) -> Self:
        return cls(
            casa=casa.casa,
            nome=_NOMES_CASA.get(casa.casa, _ASSEMBLEIAS),
            vagas=casa.vagas,
            vagas_simuladas=casa.vagas_simuladas,
            ufs_sem_votos=list(casa.ufs_sem_votos),
            legendas=[
                LegendaCadeirasJson(legenda=chave, cadeiras=valor)
                for chave, valor in _ranked(casa.cadeiras_por_legenda())
            ],
            partidos=_parties(casa.cadeiras_por_partido()),
            ufs=[CasaUfJson.from_domain(item) for item in casa.ufs],
        )


class CandidatoJson(BaseModel):
    numero: int
    partido: int
    votos: int
    fatia: str

    @classmethod
    def from_domain(cls, item: VotoCandidato, validos: int) -> Self:
        share = Fraction(item.votos, validos) if validos else Fraction(0)
        return cls(
            numero=item.numero, partido=item.partido, votos=item.votos, fatia=format_percent(share)
        )


class SenadoUfJson(BaseModel):
    uf: str
    votos_validos: int
    eleitos: list[CandidatoJson]
    empate: bool

    @classmethod
    def from_domain(cls, item: ResultadoSenado) -> Self:
        return cls(
            uf=item.uf,
            votos_validos=item.votos_validos,
            eleitos=[
                CandidatoJson.from_domain(eleito, item.votos_validos) for eleito in item.eleitos
            ],
            empate=item.empate,
        )


class SenadoJson(BaseModel):
    vagas: int
    vagas_simuladas: int
    ufs_sem_votos: list[str]
    partidos: list[PartidoCadeirasJson]
    ufs: list[SenadoUfJson]


class GovernoUfJson(BaseModel):
    uf: str
    situacao: str
    votos_validos: int
    candidatos: list[CandidatoJson]
    empate: bool

    @classmethod
    def from_domain(cls, item: ResultadoGoverno) -> Self:
        return cls(
            uf=item.uf,
            situacao=item.situacao,
            votos_validos=item.votos_validos,
            candidatos=[
                CandidatoJson.from_domain(candidato, item.votos_validos)
                for candidato in item.candidatos
            ],
            empate=item.empate,
        )


class GovernoPartidoJson(BaseModel):
    partido: int
    eleitos: int
    segundo_turno: int


class GovernoJson(BaseModel):
    ufs_sem_votos: list[str]
    partidos: list[GovernoPartidoJson]
    ufs: list[GovernoUfJson]


class ForcaPartidoJson(BaseModel):
    partido: int
    legenda: str
    camara: int
    assembleias: int
    senado: int
    governadores: int
    governadores_segundo_turno: int

    @classmethod
    def from_domain(cls, item: ForcaPartido) -> Self:
        return cls(
            partido=item.partido,
            legenda=item.legenda,
            camara=item.camara,
            assembleias=item.assembleias,
            senado=item.senado,
            governadores=item.governadores,
            governadores_segundo_turno=item.governadores_segundo_turno,
        )


class CadeirasJson(BaseModel):
    ano: int
    turno: int
    gerado_em: str
    estimativa: bool
    legendas: list[LegendaJson]
    casas: list[CasaJson]
    senado: SenadoJson
    governo: GovernoJson
    partidos: list[ForcaPartidoJson]
    descartados: int
    notas: list[str]

    @classmethod
    def from_domain(cls, gravada: SimulacaoGravada) -> Self:
        simulacao = gravada.simulacao
        return cls(
            ano=simulacao.ano,
            turno=simulacao.turno,
            gerado_em=gravada.gerado_em.isoformat(),
            estimativa=True,
            legendas=_legendas(simulacao.registro),
            casas=[
                CasaJson.from_domain(simulacao.camara),
                CasaJson.from_domain(simulacao.assembleias),
            ],
            senado=_senado(simulacao),
            governo=_governo(simulacao),
            partidos=[ForcaPartidoJson.from_domain(item) for item in simulacao.partidos()],
            descartados=simulacao.descartados,
            notas=list(NOTAS),
        )


def _legendas(registro: RegistroPartidario) -> list[LegendaJson]:
    federadas = {partido for federacao in registro.federacoes for partido in federacao.partidos}
    rows = [
        LegendaJson(
            codigo=federacao.codigo,
            sigla=federacao.sigla,
            nome=federacao.nome,
            federacao=True,
            partidos=list(federacao.partidos),
        )
        for federacao in registro.federacoes
    ]
    rows.extend(
        LegendaJson(
            codigo=str(partido),
            sigla=str(partido),
            nome=f"Partido {partido}",
            federacao=False,
            partidos=[partido],
        )
        for partido in sorted(registro.partidos - federadas)
    )
    return rows


def _senado(simulacao: SimulacaoCadeiras) -> SenadoJson:
    senado = simulacao.senado
    return SenadoJson(
        vagas=senado.vagas,
        vagas_simuladas=senado.vagas_simuladas,
        ufs_sem_votos=list(senado.ufs_sem_votos),
        partidos=_parties(senado.cadeiras_por_partido()),
        ufs=[SenadoUfJson.from_domain(item) for item in senado.ufs],
    )


def _governo(simulacao: SimulacaoCadeiras) -> GovernoJson:
    governo = simulacao.governo
    eleitos = governo.eleitos_por_partido()
    segundo = governo.segundo_turno_por_partido()
    partidos = sorted(
        set(eleitos) | set(segundo), key=lambda p: (-eleitos.get(p, 0), -segundo.get(p, 0), p)
    )
    return GovernoJson(
        ufs_sem_votos=list(governo.ufs_sem_votos),
        partidos=[
            GovernoPartidoJson(
                partido=p, eleitos=eleitos.get(p, 0), segundo_turno=segundo.get(p, 0)
            )
            for p in partidos
        ],
        ufs=[GovernoUfJson.from_domain(item) for item in governo.ufs],
    )


def _ranked(counts: dict[str, int]) -> list[tuple[str, int]]:
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _parties(counts: dict[int, int]) -> list[PartidoCadeirasJson]:
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [PartidoCadeirasJson(partido=partido, cadeiras=valor) for partido, valor in ordered]
