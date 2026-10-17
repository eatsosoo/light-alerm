"""Thread-safe request records and log correlation for API and desktop jobs."""

import copy
import logging
import threading
from collections import OrderedDict
from contextvars import ContextVar
from datetime import datetime

request_id = ContextVar("alarm_request_id", default="-")


class RequestContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id.get()
        return True


class RequestHistory(logging.Handler):
    TERMINAL = {"completed", "partial", "failed", "cancelled", "superseded"}

    def __init__(self, limit=200, event_limit=500):
        super().__init__(logging.INFO)
        self.limit = limit
        self.event_limit = event_limit
        self._records = OrderedDict()
        self._records_lock = threading.RLock()

    @staticmethod
    def timestamp():
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def create(self, job_id, metadata):
        with self._records_lock:
            self._records[job_id] = {
                "job_id": job_id, "status": "queued", "created_at": self.timestamp(),
                "started_at": None, "finished_at": None, "source": metadata.get("source", "unknown"),
                "mode": metadata.get("mode", ""), "scope": metadata.get("scope", ""),
                "duration": metadata.get("duration"), "target_count": metadata.get("target_count"),
                "result": None, "message": "", "events": [], "events_dropped": 0,
                "counts": None,
            }
            self._prune()

    def update(self, job_id, **fields):
        with self._records_lock:
            record = self._records.get(job_id)
            if record is not None:
                record.update(fields)
                self._prune()

    def _prune(self):
        completed = [key for key, record in self._records.items() if record["status"] in self.TERMINAL]
        for key in completed[:-self.limit]:
            del self._records[key]

    def emit(self, record):
        job_id = request_id.get()
        if job_id == "-":
            return
        try:
            event = {
                "time": datetime.fromtimestamp(record.created).astimezone().isoformat(timespec="seconds"),
                "level": record.levelname, "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info:
                event["message"] += "\n" + logging.Formatter().formatException(record.exc_info)
            with self._records_lock:
                item = self._records.get(job_id)
                if item is not None:
                    item["events"].append(event)
                    if len(item["events"]) > self.event_limit:
                        del item["events"][0]
                        item["events_dropped"] += 1
        except Exception:
            self.handleError(record)

    def get(self, job_id, include_events=True):
        with self._records_lock:
            record = self._records.get(job_id)
            if record is None:
                return None
            return copy.deepcopy({key: value for key, value in record.items()
                                  if include_events or key != "events"})

    def list(self):
        with self._records_lock:
            return [copy.deepcopy({key: value for key, value in item.items()
                                   if key not in ("events", "result")})
                    for item in reversed(self._records.values())]
