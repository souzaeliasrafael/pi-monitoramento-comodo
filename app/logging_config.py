"""Logs rotativos locais; mensagens controladas, sem credenciais ou payloads brutos."""

from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import PROJECT_ROOT


def configure_logging(directory: Path = PROJECT_ROOT / "logs"):
    directory.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if any(getattr(handler, "iot_handler", False) for handler in root.handlers):
        return
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    for handler in [logging.StreamHandler(), RotatingFileHandler(directory / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")]:
        handler.setFormatter(formatter)
        handler.iot_handler = True
        root.addHandler(handler)
    root.setLevel(logging.INFO)


def command_entrypoint(function):
    """CLI falha com status não zero e mensagem segura, sem traceback bruto."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            configure_logging()
            return function(*args, **kwargs)
        except KeyboardInterrupt:
            logging.getLogger(function.__module__).info("Execução interrompida pelo usuário.")
            return 130
        except Exception as error:
            # Não incluir str(error): drivers e validações externas podem conter segredos.
            logging.getLogger(function.__module__).error(
                "Operação não concluída (%s). Confira .env, permissões do banco, histórico suficiente e modelo. Consulte README: solução de problemas.",
                type(error).__name__)
            return 1
    return wrapped
