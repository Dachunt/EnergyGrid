import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger

# Crear directorio de logs si no existe
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "energygrid.log")


def setup_logging():
    json_formatter = jsonlogger.JsonFormatter(
        fmt="%(timestamp)s %(level)s %(name)s %(module)s %(message)s",
        rename_fields={"levelname": "level", "asctime": "timestamp"},
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Handler 1: archivo con rotación (10MB x 5 archivos)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(json_formatter)

    # Handler 2: stdout para docker compose logs
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(json_formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, stdout_handler],
    )
