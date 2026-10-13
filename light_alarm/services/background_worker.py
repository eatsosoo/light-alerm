"""One event loop shared by HTTP requests and desktop commands."""

import asyncio
import logging
import threading
from collections import OrderedDict
from concurrent.futures import TimeoutError as FutureTimeoutError
from uuid import uuid4

from light_alarm.services.request_history import request_id

logger = logging.getLogger(__name__)


class BackgroundWorker:
    def __init__(self, history):
        self.history = history
        self.loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._lock = threading.Lock()
        self._closed = False
        self._jobs = OrderedDict()
        self.thread = threading.Thread(target=self._run, name="alarm-worker", daemon=True)
        self.thread.start()
        self._ready.wait()

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.call_soon(self._ready.set)
        try:
            self.loop.run_forever()
        finally:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.run_until_complete(self.loop.shutdown_default_executor())
            self.loop.close()

    def submit(self, coroutine):
        with self._lock:
            if self._closed:
                coroutine.close()
                raise RuntimeError("Application is shutting down.")
            return asyncio.run_coroutine_threadsafe(coroutine, self.loop)

    def submit_tracked(self, coroutine, metadata):
        job_id = uuid4().hex
        self.history.create(job_id, metadata)
        tracked = self._run_tracked(job_id, coroutine)
        try:
            future = self.submit(tracked)
        except Exception:
            coroutine.close()
            self.history.update(job_id, status="failed", finished_at=self.history.timestamp(),
                                message="Application is shutting down.")
            raise
        with self._lock:
            self._jobs[job_id] = future
            # Retain active jobs and the latest 200 completed jobs.
            completed = [key for key, item in self._jobs.items() if item.done()]
            for key in completed[:-200]:
                self._jobs.pop(key, None)
        return job_id, future

    def submit_job(self, coroutine, metadata):
        job_id, _ = self.submit_tracked(coroutine, metadata)
        return job_id

    async def _run_tracked(self, job_id, coroutine):
        token = request_id.set(job_id)
        self.history.update(job_id, status="running", started_at=self.history.timestamp())
        logger.info("Request started")
        try:
            result = await coroutine
            total = len(result["devices"])
            status = "completed"
            if result["superseded"] == total and total:
                status = "superseded"
            elif result["failure"] == total and total:
                status = "failed"
            elif result["failure"] or result["superseded"]:
                status = "partial"
            logger.info("Request finished | status=%s", status)
            self.history.update(job_id, status=status, result=result, target_count=total,
                                counts={key: result[key] for key in ("success", "failure", "superseded")},
                                finished_at=self.history.timestamp())
            return result
        except asyncio.CancelledError:
            logger.info("Request cancelled")
            self.history.update(job_id, status="cancelled", finished_at=self.history.timestamp())
            raise
        except Exception as error:
            logger.exception("Request failed")
            self.history.update(job_id, status="failed", finished_at=self.history.timestamp(),
                                message=str(error))
            raise
        finally:
            request_id.reset(token)

    def get_job(self, job_id):
        record = self.history.get(job_id, include_events=False)
        if record is not None and record["message"]:
            record["message"] = "Command failed; see system logs with this request ID."
        return record

    async def _cancel_pending(self):
        current = asyncio.current_task()
        # Avoid interrupting TURN_OFF cleanup on tasks already being cancelled.
        tasks = [task for task in asyncio.all_tasks() if task is not current]
        for task in tasks:
            if not task.cancelling():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
        cleanup = asyncio.run_coroutine_threadsafe(self._cancel_pending(), self.loop)
        try:
            cleanup.result(timeout=20)
        except FutureTimeoutError:
            logger.error("Shutdown timed out while waiting for device cleanup.")
            return
        except Exception:
            logger.exception("Background worker shutdown failed.")
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=10)
