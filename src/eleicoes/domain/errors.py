"""Erros de domínio. Mensagens internas em inglês; o CLI traduz para o usuário."""


class ElectionError(Exception):
    """Falha esperada do domínio ou da borda de IO traduzida para o domínio."""


class InvalidElectionYearError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"invalid election year: {value}")


class MissingElectionYearError(ElectionError):
    def __init__(self) -> None:
        super().__init__("election year was not provided")


class InvalidTurnoError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"invalid turno: {value}")


class InvalidUfError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"invalid UF: {value}")


class InvalidRemoteZipError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"invalid remote zip: {value}")


class InvalidPackageRefError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"invalid package reference: {value}")


class EmptyElectionScopeError(ElectionError):
    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f"election scope requires at least one {field}")


class TransportError(ElectionError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class UnexpectedHttpStatusError(TransportError):
    def __init__(self, status_code: int, filename: str) -> None:
        self.status_code = status_code
        self.filename = filename
        super().__init__(f"unexpected HTTP {status_code} for {filename}")


class CkanPayloadError(TransportError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidGenerationError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"invalid generation stamp: {value}")


class SchemaMismatchError(ElectionError):
    def __init__(self, member: str) -> None:
        self.member = member
        super().__init__(f"unexpected csv header: {member}")


class MissingIndexError(ElectionError):
    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"missing index: {path}")


class ArchiveUnreadableError(ElectionError):
    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"unreadable archive: {path}")


class DatabaseConfigError(ElectionError):
    def __init__(self, missing: tuple[str, ...]) -> None:
        self.missing = missing
        joined = ", ".join(missing)
        super().__init__(f"missing database configuration: {joined}")


class UnknownCorrespondenceStatusError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"unknown correspondence status: {value}")


class InvalidCorrespondenceRecordError(ElectionError):
    def __init__(self, field: object) -> None:
        self.field = field
        super().__init__(f"invalid correspondence record: {field}")


class InvalidRequestPaceError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"invalid request pace: {value}")


class InvalidUrnaCodeError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"invalid urna code: {value}")


class UnexpectedTsePayloadError(ElectionError):
    def __init__(self) -> None:
        super().__init__("Resposta do TSE fora do formato esperado.")


class TseBlockedError(ElectionError):
    def __init__(self) -> None:
        super().__init__(
            "O TSE bloqueou o endereço por excesso de requisições. "
            "A espera de 10 minutos não liberou o acesso."
        )


class AnnouncedFilesMissingError(ElectionError):
    def __init__(self) -> None:
        super().__init__(
            "Download interrompido: o TSE respondeu 404 para arquivos anunciados. "
            "Novas tentativas podem bloquear o IP."
        )


class InvalidBoletimContentError(ElectionError):
    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f"invalid boletim field: {field}")


class InvalidBoletimError(ElectionError):
    def __init__(self, arquivo: str) -> None:
        self.arquivo = arquivo
        super().__init__(f"invalid boletim: {arquivo}")


class InvalidOrdemError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"invalid ordem: {value}")


class InvalidNivelError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"invalid nivel: {value}")


class InvalidCargoError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"invalid cargo: {value}")


class InvalidNumeroError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"invalid numero: {value}")


class InvalidBoletimConsultaError(ElectionError):
    def __init__(self, field: object) -> None:
        self.field = field
        super().__init__(f"invalid boletim consultation: {field}")


class InvalidStoredReportError(ElectionError):
    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f"invalid stored power report: {field}")


class InvalidGroupSpanError(ElectionError):
    def __init__(self) -> None:
        super().__init__("A faixa de grupos é inválida.")


class FewMunicipalitiesError(ElectionError):
    def __init__(self) -> None:
        super().__init__("Menos de 3 municípios com votos válidos.")


class EmptyStoredCellsError(ElectionError):
    def __init__(self) -> None:
        super().__init__("Não há células gravadas para este cargo.")


class FewClassesError(ElectionError):
    def __init__(self) -> None:
        super().__init__("Não há classes suficientes para separar.")


class MissingCrossReportError(ElectionError):
    def __init__(self) -> None:
        super().__init__("Gere o relatório presidente × governador antes.")


def comando_relatorio_poder(cargo: str) -> str:
    return f"uv run python scripts/relatorio_poder.py --cargo {cargo} --sem-navegador"


class MissingPowerReportError(ElectionError):
    def __init__(self, cargo: str) -> None:
        self.cargo = cargo
        super().__init__(
            f"O relatório de poder de {cargo} ainda não foi gravado. "
            f"Gere com: {comando_relatorio_poder(cargo)}"
        )


class MissingStrengthSourcesError(ElectionError):
    def __init__(self, cargos: tuple[str, ...]) -> None:
        self.cargos = cargos
        comandos = "; ".join(comando_relatorio_poder(cargo) for cargo in cargos)
        super().__init__(
            "Nenhum relatório de poder usado pelo placar de força foi gravado. "
            f"Gere com: {comandos}"
        )


class FewStatesError(ElectionError):
    def __init__(self) -> None:
        super().__init__("Menos de 2 UFs para validar.")


class InconsistentCellError(ElectionError):
    def __init__(self) -> None:
        super().__init__("Célula municipal inconsistente.")


class StoredReadError(ElectionError):
    def __init__(self) -> None:
        super().__init__("Não foi possível ler o relatório gravado.")


class CargoSemCelulasError(ElectionError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class UnusableGroupCountError(ElectionError):
    def __init__(self) -> None:
        super().__init__("O número de grupos não cabe nos municípios.")


SCHEMA_OUTDATED_HINT = (
    "O esquema do banco está desatualizado. Rode make migrate "
    "(ou python -m eleicoes migrar) e tente de novo."
)


class SchemaOutdatedError(ElectionError):
    def __init__(self, current: tuple[str, ...], expected: str) -> None:
        self.current = current
        self.expected = expected
        found = ", ".join(current) or "none"
        super().__init__(f"database schema revision {found} is not {expected}")


class InvalidSeatRuleError(ElectionError):
    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f"invalid seat simulation input: {field}")


class UnknownPartyRegistryError(ElectionError):
    def __init__(self, ano: int) -> None:
        self.ano = ano
        super().__init__(f"Não há partidos e federações cadastrados para {ano}.")


class UnsupportedSeatTurnError(ElectionError):
    def __init__(self, turno: int) -> None:
        self.turno = turno
        super().__init__(
            f"A simulação de cadeiras usa só os votos do 1º turno; o turno {turno} não se aplica."
        )


class MissingSeatReportError(ElectionError):
    def __init__(self, cargos: tuple[str, ...]) -> None:
        self.cargos = cargos
        listed = ", ".join(cargos)
        super().__init__(
            f"Os votos por candidato de {listed} ainda não foram gravados. "
            f"Gere com: {comando_relatorio_cadeiras()}"
        )


class InvalidMunicipalYearError(InvalidElectionYearError):
    """Ano válido, mas sem eleição municipal (o ciclo municipal é múltiplo de 4)."""


class DuplicateMayorError(ElectionError):
    def __init__(self, uf: str, ue: str) -> None:
        self.uf = uf
        self.ue = ue
        super().__init__(f"more than one elected mayor in {uf} {ue}")


class InvalidMunicipalRowError(ElectionError):
    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f"invalid municipal row field: {field}")


class MissingMunicipalResultsError(ElectionError):
    def __init__(self, year: int) -> None:
        self.year = year
        super().__init__(
            f"Os resultados municipais de {year} ainda não foram importados. "
            f"Rode: python -m eleicoes download-municipais --ano {year} e "
            f"python -m eleicoes import-municipais --ano {year}."
        )


def comando_relatorio_cadeiras() -> str:
    return "uv run python scripts/relatorio_cadeiras.py"


def comando_municipais_2024() -> str:
    return "make download-municipais && make import-municipais"


class InvalidRecorteError(ElectionError):
    def __init__(self) -> None:
        super().__init__("Recorte inválido. Use regiao (NO, NE, CO, SE ou S) ou uf, não os dois.")


class EmptyRecorteError(ElectionError):
    def __init__(self, recorte: str, cargo: str) -> None:
        self.recorte = recorte
        self.cargo = cargo
        super().__init__(f"Não há municípios gravados para {cargo} no recorte {recorte}.")
