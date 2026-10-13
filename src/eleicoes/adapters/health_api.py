"""Health route. The application factory lives in the composition root."""


def health() -> dict[str, str]:
    return {"status": "ok"}
