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
