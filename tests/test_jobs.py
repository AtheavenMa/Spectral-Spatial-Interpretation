"""Regression tests for unexpected worker exceptions and cancellation lifecycle."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time
import unittest
from unittest.mock import patch

from lab.jobs import Jobs
from lab.runtime import raise_if_cancelled


def terminal(queue: Jobs, job_id: str, timeout: float = 4.0):
    stop = time.monotonic() + timeout
    while time.monotonic() < stop:
        result = queue.get(job_id)
        if result["status"] != "running":
            return result
        time.sleep(.01)
    raise AssertionError("A worker remained in 'running' after its callable finished")


class WorkerReliabilityTests(unittest.TestCase):
    def test_unexpected_model_exception_becomes_terminal_error(self):
        queue = Jobs()
        with patch("lab.engine.run", side_effect=RuntimeError("internal torch failure")):
            job_id = queue.start({"grid": 4})
            result = terminal(queue, job_id)
            self.assertEqual(result["status"], "error")
            self.assertEqual(result["error"], "Inference failed. Check the server logs.")
            self.assertIsNone(result["result"])
            # A failed worker must no longer block the single-slot scheduler.
            next_job = queue.start({"grid": 8})
            self.assertEqual(terminal(queue, next_job)["status"], "error")

    def test_cancelled_job_releases_slot(self):
        queue = Jobs()
        running = Event()

        def work(**kwargs):
            running.set()
            while True:
                raise_if_cancelled()
                time.sleep(.005)

        with patch("lab.engine.run", side_effect=work):
            job_id = queue.start({"grid": 4})
            self.assertTrue(running.wait(2))
            queue.cancel(job_id)
            result = terminal(queue, job_id)
            self.assertEqual(result["status"], "cancelled")
            self.assertIsNone(result["result"])
            # Avoid leaving the service permanently "busy" following cancellation.
            another = queue.start({"grid": 4})
            queue.cancel(another)
            self.assertEqual(terminal(queue, another)["status"], "cancelled")

if __name__ == "__main__":
    unittest.main()
