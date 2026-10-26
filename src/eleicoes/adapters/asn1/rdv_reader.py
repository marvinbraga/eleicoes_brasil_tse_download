"""Decodifica rdv.dat BER com a especificação 2026 e recontabiliza os votos por cargo."""

from collections.abc import Mapping
from pathlib import Path
from typing import Final, cast

from eleicoes.domain.errors import InvalidBoletimContentError
from eleicoes.domain.integridade_urna import ChaveVoto, RegistroDigital

_SPEC: Final = Path(__file__).resolve().parent / "rdv.asn1"
_ENTIDADE: Final = "EntidadeResultadoRDV"
_VOTA: Final = "eleicoesVota"
# Os tipos do RDV que o BU soma numa mesma linha, com o nome que o BU usa.
_COMO_NO_BU: Final[Mapping[str, str]] = {
    "branco": "branco",
    "brancoAposSuspensao": "branco",
    "nulo": "nulo",
    "nuloAposSuspensao": "nulo",
    "nuloPorRepeticao": "nulo",
    "nuloCargoSemCandidato": "cargoSemCandidato",
    "nuloAposSuspensaoCargoSemCandidato": "cargoSemCandidato",
}
_NOMINAL: Final = "nominal"
_LEGENDA: Final = "legenda"
_DIGITOS_DO_PARTIDO: Final = 2


class Asn1RdvReader:
    def __init__(self) -> None:
        import asn1tools

        self._spec = asn1tools.compile_files(str(_SPEC), codec="ber")

    def read(self, payload: bytes) -> RegistroDigital:
        try:
            decoded = self._spec.decode(_ENTIDADE, payload)
        except Exception as exc:
            raise InvalidBoletimContentError("rdv") from exc
        return _registro(cast(Mapping[str, object], decoded))


def _registro(raw: Mapping[str, object]) -> RegistroDigital:
    rdv = _mapa(raw["rdv"])
    identificacao = _mapa(rdv["identificacao"])
    municipio_zona = _mapa(identificacao["municipioZona"])
    carga = _mapa(_mapa(_mapa(raw["urna"])["correspondenciaResultado"])["carga"])
    escolha, eleicoes = cast(tuple[str, list[object]], rdv["eleicoes"])
    if escolha != _VOTA:
        raise InvalidBoletimContentError("rdv")
    cargos: dict[str, dict[ChaveVoto, int]] = {}
    for eleicao in eleicoes:
        for votos_cargo in cast(list[object], _mapa(eleicao)["votosCargos"]):
            _somar(cargos, _mapa(votos_cargo))
    return RegistroDigital(
        int(cast(int, municipio_zona["municipio"])),
        int(cast(int, municipio_zona["zona"])),
        int(cast(int, identificacao["secao"])),
        int(cast(int, carga["numeroInternoUrna"])),
        cargos,
    )


def _somar(cargos: dict[str, dict[ChaveVoto, int]], votos_cargo: Mapping[str, object]) -> None:
    _tipo, cargo = cast(tuple[str, object], votos_cargo["idCargo"])
    contagem = cargos.setdefault(str(cargo), {})
    for voto in cast(list[object], votos_cargo["votos"]):
        chave = _chave(_mapa(voto))
        contagem[chave] = contagem.get(chave, 0) + 1


def _chave(voto: Mapping[str, object]) -> ChaveVoto:
    tipo = str(voto["tipoVoto"])
    if tipo == _LEGENDA:
        # O RDV guarda a digitação inteira ("1103", "131"); a legenda é o partido dos dois
        # primeiros dígitos, como o BU soma.
        return (tipo, int(str(voto["digitacao"])[:_DIGITOS_DO_PARTIDO]))
    if tipo == _NOMINAL:
        return (tipo, int(str(voto["digitacao"])))
    como = _COMO_NO_BU.get(tipo)
    if como is None:
        raise InvalidBoletimContentError("rdv")
    return (como, None)


def _mapa(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise InvalidBoletimContentError("rdv")
    return cast(Mapping[str, object], value)
