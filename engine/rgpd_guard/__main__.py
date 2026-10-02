# @spec docs/BACKLOG.md#RG-018 | docs/DAT.md#deploiement
"""Point d'entrée : `python -m rgpd_guard` lance l'API sur un seul worker (le coffre vit en mémoire)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import uvicorn


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("RGPD_GUARD_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    reload = os.environ.get("RGPD_GUARD_RELOAD", "false") == "true"
    uvicorn.run(
        "rgpd_guard.api:create_app",
        factory=True,
        host=os.environ.get("RGPD_GUARD_HOST", "0.0.0.0"),  # noqa: S104 (exposé uniquement via 127.0.0.1 par Compose)
        port=int(os.environ.get("RGPD_GUARD_PORT", "8742")),
        workers=1,
        access_log=False,
        reload=reload,
        # Surveillance limitée au paquet : sans watchfiles, le scrutateur d'uvicorn parcourrait
        # aussi l'environnement virtuel monté en dev (plus d'un gigaoctet, un cœur occupé en continu).
        reload_dirs=[str(Path(__file__).resolve().parent)] if reload else None,
    )


if __name__ == "__main__":
    main()
