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
