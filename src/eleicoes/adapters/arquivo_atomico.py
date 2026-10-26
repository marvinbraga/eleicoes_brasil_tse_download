"""Grava um relatório de uma vez: quem lê no meio da gravação recebe o arquivo inteiro."""

import os
import tempfile
from pathlib import Path


def gravar_texto(destino: Path, texto: str) -> None:
    """Escreve num temporário da mesma pasta e troca pelo destino com os.replace.

    O frontend lê os relatórios enquanto o acompanhamento do 2º turno os refaz. Gravar
    direto no destino deixava, por um instante, um HTML cortado, e o mapa abria em branco.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    descritor, temporario = tempfile.mkstemp(
        prefix=f".{destino.name}.", suffix=".tmp", dir=destino.parent
    )
    try:
        with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
            arquivo.write(texto)
        os.chmod(temporario, 0o644)
        os.replace(temporario, destino)
    except BaseException:
        Path(temporario).unlink(missing_ok=True)
        raise
