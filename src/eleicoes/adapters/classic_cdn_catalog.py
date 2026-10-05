from typing import Final

from eleicoes.domain.values import DiscoveryRequest, ElectionYear, RemoteZip, Turno, Uf

DEFAULT_CDN_ROOT: Final = "https://cdn.tse.jus.br/estatistica/sead/eleicoes"
_FILENAME: Final = "bu_imgbu_logjez_rdv_vscmr_{year}_{turno}t_{uf}.zip"


class ClassicCdnCatalog:
    """Monta as URLs históricas de arqurnatot para os turnos e UFs pedidos."""

    def discover(self, request: DiscoveryRequest) -> tuple[RemoteZip, ...]:
        directory = _directory(request)
        return tuple(
            _archive(directory, request.year, turno, uf)
            for turno in request.turnos
            for uf in request.ufs
        )


def _directory(request: DiscoveryRequest) -> str:
    if request.cdn_directory is not None:
        return request.cdn_directory
    return f"{DEFAULT_CDN_ROOT}/eleicoes{request.year.value}/arqurnatot"


def _archive(directory: str, year: ElectionYear, turno: Turno, uf: Uf) -> RemoteZip:
    filename = _FILENAME.format(year=year.value, turno=turno.value, uf=uf.code)
    return RemoteZip(url=f"{directory}/{filename}", filename=filename)
