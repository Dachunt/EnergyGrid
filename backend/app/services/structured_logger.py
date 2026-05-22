import json
import logging
from datetime import datetime, timezone


_logger = logging.getLogger("energygrid")
if not _logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)


def log_event(level: int, **fields):
    fields.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    message = json.dumps(fields)
    _logger.log(level, message)
