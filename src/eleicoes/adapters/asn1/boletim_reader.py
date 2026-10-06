"""Decodifica bu.dat BER com a especificação 2026 e devolve um Boletim."""

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final, NamedTuple, cast

from eleicoes.domain.boletim import Boletim, VoteLine
from eleicoes.domain.errors import InvalidBoletimContentError, InvalidBoletimError

_SPEC: Final = Path(__file__).resolve().parent / "bu.asn1"
_OFFICIAL: Final = "oficial"
_BULLETIN_ENVELOPE: Final = "envelopeBoletimUrna"
_CONSTITUTIONAL: Final = "cargoConstitucional"
_FREE_CARGO: Final = "numeroCargoConsultaLivre"


class Asn1BoletimReader:
    def __init__(self) -> None:
        self._spec = _compile()

    def read(self, arquivo: str, payload: bytes) -> Boletim:
        try:
            return self._parsed(arquivo, payload)
        except InvalidBoletimContentError as exc:
            raise InvalidBoletimError(arquivo) from exc

    def _parsed(self, arquivo: str, payload: bytes) -> Boletim:
        envelope = self._decode("EntidadeEnvelopeGenerico", payload)
        _require_envelope(envelope)
        bulletin = self._decode("EntidadeBoletimUrna", _octet(envelope.get("conteudo")))
        return _to_boletim(arquivo, bulletin)

    def _decode(self, name: str, payload: bytes) -> Mapping[str, object]:
        try:
            decoded = self._spec.decode(name, payload)
        except Exception as exc:
            raise InvalidBoletimContentError("asn1") from exc
        return _mapping(decoded, name)


class _Compiled:
    def __init__(self, inner: object) -> None:
        self._decode = _bind(inner)

    def decode(self, name: str, data: bytes) -> object:
        return self._decode(name, data)


class _Section(NamedTuple):
    municipio: int
    zona: int
    local: int
    secao: int


class _Machine(NamedTuple):
    versao_urna: str
    numero_interno_urna: int
    data_hora_carga: str
    codigo_carga: str
    codigo_midia: str


class _Counts(NamedTuple):
    eleitores_computados: int
    indicador_habilitacao: int
    qtd_biometria: int
    qtd_manual: int
    data_hora_emissao: str


class _Election(NamedTuple):
    id_eleicao: int
    eleitores_aptos: int
    qtd_comparecimento: int
    qtd_eleitores_complemento: int


def _compile() -> _Compiled:
    import asn1tools

    return _Compiled(asn1tools.compile_files(str(_SPEC), codec="ber"))


def _bind(inner: object) -> Callable[[str, bytes], object]:
    decode = getattr(inner, "decode", None)
    if not callable(decode):
        raise InvalidBoletimContentError("spec")
    return cast(Callable[[str, bytes], object], decode)


def _require_envelope(raw: Mapping[str, object]) -> None:
    if raw.get("tipoEnvelope") != _BULLETIN_ENVELOPE:
        raise InvalidBoletimContentError("tipoEnvelope")
    if raw.get("fase") != _OFFICIAL:
        raise InvalidBoletimContentError("fase")


def _to_boletim(arquivo: str, raw: Mapping[str, object]) -> Boletim:
    if raw.get("fase") != _OFFICIAL:
        raise InvalidBoletimContentError("fase")
    section = _section(raw)
    machine = _machine(raw)
    counts = _counts(raw)
    return Boletim(
        arquivo=arquivo,
        fase=_OFFICIAL,
        municipio=section.municipio,
        zona=section.zona,
        local=section.local,
        secao=section.secao,
        data_hora_emissao=counts.data_hora_emissao,
        versao_urna=machine.versao_urna,
        numero_interno_urna=machine.numero_interno_urna,
        data_hora_carga=machine.data_hora_carga,
        codigo_carga=machine.codigo_carga,
        codigo_midia=machine.codigo_midia,
        eleitores_computados=counts.eleitores_computados,
        indicador_habilitacao=counts.indicador_habilitacao,
        qtd_biometria=counts.qtd_biometria,
        qtd_manual=counts.qtd_manual,
        votos=_vote_lines(raw),
    )


def _section(raw: Mapping[str, object]) -> _Section:
    ident = _mapping(raw.get("identificacaoSecao"), "secao")
    zone = _mapping(ident.get("municipioZona"), "municipio")
    return _Section(
        municipio=_integer(zone.get("municipio"), "municipio"),
        zona=_integer(zone.get("zona"), "zona"),
        local=_integer(ident.get("local"), "local"),
        secao=_integer(ident.get("secao"), "secao"),
    )


def _machine(raw: Mapping[str, object]) -> _Machine:
    urna = _mapping(raw.get("urna"), "urna")
    correspondencia = _mapping(urna.get("correspondenciaResultado"), "carga")
    carga = _mapping(correspondencia.get("carga"), "carga")
    origem = _mapping(carga.get("origemCarga"), "codigo_midia")
    return _Machine(
        versao_urna=_text(urna.get("versaoVotacao"), "versao_urna"),
        numero_interno_urna=_integer(carga.get("numeroInternoUrna"), "numero_interno_urna"),
        data_hora_carga=_text(carga.get("dataHoraCarga"), "data_hora_carga"),
        codigo_carga=_text(carga.get("codigoCarga"), "codigo_carga"),
        codigo_midia=_text(origem.get("codigoMidia"), "codigo_midia"),
    )


def _counts(raw: Mapping[str, object]) -> _Counts:
    habilitacao = _mapping(raw.get("resumoHabilitacao"), "habilitacao")
    return _Counts(
        eleitores_computados=_integer(raw.get("qtdEleitoresComputados"), "eleitores_computados"),
        indicador_habilitacao=_integer(habilitacao.get("indicador"), "indicador_habilitacao"),
        qtd_biometria=_integer(habilitacao.get("qtdBiometria"), "qtd_biometria"),
        qtd_manual=_integer(habilitacao.get("qtdManual"), "qtd_manual"),
        data_hora_emissao=_text(raw.get("dataHoraEmissao"), "data_hora_emissao"),
    )


def _vote_lines(raw: Mapping[str, object]) -> tuple[VoteLine, ...]:
    lines: list[VoteLine] = []
    for election in _items(raw.get("resultadosVotacaoPorEleicao"), "eleicoes"):
        lines.extend(_election_lines(_mapping(election, "eleicao")))
    return tuple(lines)


def _election_lines(raw: Mapping[str, object]) -> tuple[VoteLine, ...]:
    header = _Election(
        id_eleicao=_integer(raw.get("idEleicao"), "id_eleicao"),
        eleitores_aptos=_integer(raw.get("qtdEleitoresAptos"), "eleitores_aptos"),
        qtd_comparecimento=_integer(raw.get("qtdComparecimento"), "qtd_comparecimento"),
        qtd_eleitores_complemento=_integer(
            raw.get("qtdEleitoresExtra"),
            "qtd_eleitores_complemento",
        ),
    )
    lines: list[VoteLine] = []
    for result in _items(raw.get("resultadosVotacao"), "resultados"):
        lines.extend(_result_lines(header, _mapping(result, "resultado")))
    return tuple(lines)


def _result_lines(header: _Election, raw: Mapping[str, object]) -> tuple[VoteLine, ...]:
    tipo_cargo = _text(raw.get("tipoCargo"), "tipo_cargo")
    comparecimento = _integer(raw.get("qtdComparecimento"), "comparecimento_cargo")
    lines: list[VoteLine] = []
    for total in _items(raw.get("totaisVotosCargo"), "cargos"):
        lines.extend(_cargo_lines(header, tipo_cargo, comparecimento, _mapping(total, "cargo")))
    return tuple(lines)


def _cargo_lines(
    header: _Election,
    tipo_cargo: str,
    comparecimento: int,
    raw: Mapping[str, object],
) -> tuple[VoteLine, ...]:
    cargo = _cargo_name(raw.get("codigoCargo"))
    ordem = _integer(raw.get("ordemImpressao"), "ordem_impressao")
    return tuple(
        _one_vote(header, tipo_cargo, comparecimento, cargo, ordem, _mapping(vote, "voto"))
        for vote in _items(raw.get("votosVotaveis"), "votos")
    )


def _one_vote(
    header: _Election,
    tipo_cargo: str,
    comparecimento: int,
    cargo: str,
    ordem: int,
    raw: Mapping[str, object],
) -> VoteLine:
    partido, numero = _identification(raw)
    return VoteLine(
        id_eleicao=header.id_eleicao,
        eleitores_aptos=header.eleitores_aptos,
        qtd_comparecimento=header.qtd_comparecimento,
        qtd_eleitores_complemento=header.qtd_eleitores_complemento,
        tipo_cargo=tipo_cargo,
        cargo=cargo,
        ordem_impressao=ordem,
        comparecimento_cargo=comparecimento,
        tipo_voto=_text(raw.get("tipoVoto"), "tipo_voto"),
        partido=partido,
        numero=numero,
        quantidade=_integer(raw.get("quantidadeVotos"), "quantidade"),
    )


def _identification(raw: Mapping[str, object]) -> tuple[int | None, int | None]:
    if "identificacaoVotavel" not in raw:
        return None, None
    value = raw["identificacaoVotavel"]
    if value is None:
        return None, None
    ident = _mapping(value, "identificacao")
    partido = _integer(ident.get("partido"), "partido")
    numero = _integer(ident.get("codigo"), "numero")
    return partido, numero


def _cargo_name(value: object) -> str:
    label, inner = _choice(value)
    if label == _CONSTITUTIONAL:
        return _text(inner, "cargo")
    if label == _FREE_CARGO:
        return str(_integer(inner, "cargo"))
    raise InvalidBoletimContentError("cargo")


def _choice(value: object) -> tuple[str, object]:
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str):
        return value[0], value[1]
    raise InvalidBoletimContentError("cargo")


def _octet(value: object) -> bytes:
    if isinstance(value, bytes) and value:
        return value
    if isinstance(value, bytearray) and value:
        return bytes(value)
    raise InvalidBoletimContentError("conteudo")


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise InvalidBoletimContentError(field)
    raw = cast(Mapping[object, object], value)
    mapped: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            raise InvalidBoletimContentError(field)
        mapped[key] = item
    return mapped


def _items(value: object, field: str) -> tuple[object, ...]:
    if isinstance(value, list):
        return tuple(cast(list[object], value))
    if isinstance(value, tuple):
        return cast(tuple[object, ...], value)
    raise InvalidBoletimContentError(field)


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidBoletimContentError(field)
    return value


def _text(value: object, field: str) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("latin-1")
    raise InvalidBoletimContentError(field)
