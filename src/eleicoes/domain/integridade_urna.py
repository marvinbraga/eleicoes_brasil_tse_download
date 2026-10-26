"""Conferência dos arquivos de uma urna: boletim (BU) × registro digital do voto (RDV) × log.

O BU é a apuração que a urna imprime e publica. O RDV guarda cada voto, um a um, em
ordem embaralhada. O log registra cada evento da urna. Os três são gravados pela mesma
urna, e cada um precisa fechar com os outros:

* o RDV recontado, cargo a cargo, dá exatamente as contagens do BU;
* o log do dia da votação registra um "voto computado" por eleitor do BU e um voto de
  presidente e de governador para cada um do BU (confirmado ou atribuído por suspensão);
* RDV, log e BU apontam a mesma seção e a mesma urna.

Urna trocada durante a votação é procedimento previsto: o pacote traz o log das duas
urnas, e os números continuam fechando. Ela é marcada à parte, não como divergência.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final

from eleicoes.domain.boletim import Boletim

CONFERE: Final = "confere"
DIVERGE: Final = "diverge"
SEM_RDV: Final = "sem_rdv"
SEM_LOG: Final = "sem_log"

# Cargos de escolha única: o log registra um voto por eleitor.
CARGOS_NO_LOG: Final[Mapping[str, str]] = {
    "presidente": "Presidente",
    "governador": "Governador",
}

ChaveVoto = tuple[str, int | None]


@dataclass(frozen=True, slots=True)
class RegistroDigital:
    """O RDV de uma seção, já somado por cargo e por chave de voto do BU."""

    municipio: int
    zona: int
    secao: int
    numero_interno_urna: int
    cargos: Mapping[str, Mapping[ChaveVoto, int]]


@dataclass(frozen=True, slots=True)
class ResumoLog:
    """Os eventos do log no dia da votação."""

    computados: int
    votos_por_cargo: Mapping[str, int]
    urnas: frozenset[str]
    logs: int = 1
    # Por urna: (votos computados, votos por cargo). O pacote de uma seção pode trazer o log
    # de urnas usadas em contingência ou na recuperação de outra seção.
    por_urna: Mapping[str, tuple[int, Mapping[str, int]]] = field(default_factory=dict)
    # Votos com o último cargo confirmado e a urna religada em seguida, sem a linha "computado".
    interrompidos: int = 0

    def contagens(self) -> tuple[int, ...]:
        """O total do pacote e o de cada urna, com e sem os votos interrompidos por queda."""
        totais = (self.computados, *(total for total, _ in self.por_urna.values()))
        return tuple(sorted({*totais, *(total + self.interrompidos for total in totais)}))


@dataclass(frozen=True, slots=True)
class Conferencia:
    municipio: int
    zona: int
    secao: int
    numero_interno_urna: int
    situacao: str
    divergencias: tuple[str, ...] = ()
    urna_trocada: bool = False
    detalhes: Mapping[str, str] = field(default_factory=dict)


def contagens_do_boletim(boletim: Boletim) -> dict[str, dict[ChaveVoto, int]]:
    """As linhas do BU com a mesma chave que o RDV usa: número no nominal, partido na legenda."""
    cargos: dict[str, dict[ChaveVoto, int]] = {}
    for linha in boletim.votos:
        if linha.tipo_voto == "nominal":
            chave: ChaveVoto = ("nominal", linha.numero)
        elif linha.tipo_voto == "legenda":
            chave = ("legenda", linha.partido)
        else:
            chave = (linha.tipo_voto, None)
        contagem = cargos.setdefault(linha.cargo, {})
        contagem[chave] = contagem.get(chave, 0) + linha.quantidade
    return cargos


def conferir(
    boletim: Boletim,
    rdv: RegistroDigital | None,
    log: ResumoLog | None,
) -> Conferencia:
    divergencias: list[str] = []
    detalhes: dict[str, str] = {}
    if rdv is not None:
        divergencias.extend(_contra_rdv(boletim, rdv, detalhes))
    if log is not None:
        divergencias.extend(_contra_log(boletim, log, detalhes))
    situacao = _situacao(divergencias, rdv, log)
    return Conferencia(
        boletim.municipio,
        boletim.zona,
        boletim.secao,
        boletim.numero_interno_urna,
        situacao,
        tuple(divergencias),
        log is not None and log.logs > 1,
        detalhes,
    )


def _situacao(divergencias: list[str], rdv: RegistroDigital | None, log: ResumoLog | None) -> str:
    if divergencias:
        return DIVERGE
    if rdv is None:
        return SEM_RDV
    if log is None:
        return SEM_LOG
    return CONFERE


def _contra_rdv(boletim: Boletim, rdv: RegistroDigital, detalhes: dict[str, str]) -> list[str]:
    found: list[str] = []
    if (rdv.municipio, rdv.zona, rdv.secao) != (boletim.municipio, boletim.zona, boletim.secao):
        found.append("rdv_outra_secao")
    if rdv.numero_interno_urna != boletim.numero_interno_urna:
        found.append("rdv_outra_urna")
    for cargo, contagem in contagens_do_boletim(boletim).items():
        recontagem = rdv.cargos.get(cargo)
        if recontagem is None:
            found.append(f"rdv_sem_cargo:{cargo}")
            continue
        if _sem_zeros(contagem) != _sem_zeros(recontagem):
            found.append(f"rdv_difere:{cargo}")
            detalhes[f"rdv:{cargo}"] = f"BU {_texto(contagem)} | RDV {_texto(recontagem)}"
    return found


def _contra_log(boletim: Boletim, log: ResumoLog, detalhes: dict[str, str]) -> list[str]:
    """Os votos por cargo já são conferidos voto a voto pelo RDV; o log confere eleitores."""
    if log.interrompidos:
        detalhes["queda"] = f"{log.interrompidos} voto(s) sem a linha 'computado' por queda"
    if boletim.eleitores_computados in log.contagens():
        return []
    partes = [f"pacote {log.computados}"]
    partes.extend(f"urna {urna} {total}" for urna, (total, _) in sorted(log.por_urna.items()))
    if log.interrompidos:
        partes.append(f"interrompidos {log.interrompidos}")
    detalhes["log"] = f"BU {boletim.eleitores_computados} | log " + ", ".join(partes)
    found = ["log_computados"]
    if f"{boletim.numero_interno_urna:08d}" not in log.urnas:
        found.append("log_sem_a_urna_do_bu")
    return found


def _sem_zeros(contagem: Mapping[ChaveVoto, int]) -> dict[ChaveVoto, int]:
    return {chave: total for chave, total in contagem.items() if total}


def _texto(contagem: Mapping[ChaveVoto, int]) -> str:
    def ordem(chave: ChaveVoto) -> tuple[str, int]:
        return (chave[0], -1 if chave[1] is None else chave[1])

    partes = []
    for chave in sorted(_sem_zeros(contagem), key=ordem):
        rotulo = chave[0] if chave[1] is None else f"{chave[0]} {chave[1]}"
        partes.append(f"{rotulo}={contagem[chave]}")
    return ", ".join(partes)
