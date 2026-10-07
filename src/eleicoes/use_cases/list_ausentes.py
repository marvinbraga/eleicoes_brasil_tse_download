"""Lista caminhos de marcadores .ausente sem consultar o TSE nem o Postgres."""

from pathlib import Path
from typing import Final

from eleicoes.domain.urna_models import URNA_COLLECTION
from eleicoes.domain.values import Turno, Uf

# Mesmo sufixo de import_boletins._ABSENT_SUFFIX. O nome de lá é privado.
_ABSENT_SUFFIX: Final = ".ausente"
_ABSENT_GLOB: Final = f"*{_ABSENT_SUFFIX}"


def list_ausentes(root: Path, turno: Turno, uf: Uf | None = None) -> tuple[str, ...]:
    """Caminhos relativos à raiz do ano, com `/`, sem o sufixo `.ausente`."""
    return tuple(_original_relative(root, path) for path in _markers(_scope(root, turno, uf)))


def _scope(root: Path, turno: Turno, uf: Uf | None) -> Path:
    folder = root / URNA_COLLECTION / f"turno-{turno.value}"
    if uf is None:
        return folder
    return folder / uf.code


def _markers(scope: Path) -> tuple[Path, ...]:
    if not scope.is_dir():
        return ()
    found = [path for path in scope.rglob(_ABSENT_GLOB) if path.is_file()]
    return tuple(sorted(found))


def _original_relative(root: Path, marker: Path) -> str:
    relative = marker.relative_to(root)
    original = relative.name.removesuffix(_ABSENT_SUFFIX)
    return relative.with_name(original).as_posix()
