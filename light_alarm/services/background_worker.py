"""One event loop shared by HTTP requests and desktop commands."""

import asyncio
import logging
import threading
from collections import OrderedDict
from concurrent.futures import TimeoutError as FutureTimeoutError
from uuid import uuid4

logger = logging.getLogger(__name__)


class BackgroundWorker:
    def __init__(self):
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

    def submit_job(self, coroutine):
        job_id = uuid4().hex
        future = self.submit(coroutine)
        with self._lock:
            self._jobs[job_id] = future
            # Retain active jobs and the latest 200 completed jobs.
            completed = [key for key, item in self._jobs.items() if item.done()]
            for key in completed[:-200]:
                self._jobs.pop(key, None)
        future.add_done_callback(lambda item: self._log_completion(job_id, item))
        return job_id

    @staticmethod
    def _log_completion(job_id, future):
        if future.cancelled():
            logger.info("Job cancelled | job_id=%s", job_id)
            return
        error = future.exception()
        if error:
            logger.error("Job failed | job_id=%s | error=%s", job_id, error,
                         exc_info=(type(error), error, error.__traceback__))

    def get_job(self, job_id):
        with self._lock:
            future = self._jobs.get(job_id)
        if future is None:
            return None
        if future.cancelled():
            return {"job_id": job_id, "status": "cancelled"}
        if not future.done():
            return {"job_id": job_id, "status": "running"}
        try:
            result = future.result()
        except Exception:
            return {"job_id": job_id, "status": "failed", "message": "Command failed; see system logs."}
        status = "completed" if not result["failure"] and not result["superseded"] else "partial"
        if result["failure"] and not result["success"] and not result["superseded"]:
            status = "failed"
        return {"job_id": job_id, "status": status, "result": result}

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
