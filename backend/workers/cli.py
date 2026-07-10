"""Background worker CLI entrypoint (Sprint 8.5)."""

from __future__ import annotations

import signal
import sys
import time

from backend.logging import setup_logging
from backend.workers.worker import Worker


def main() -> None:
    setup_logging()
    worker = Worker()
    worker.start()

    def _shutdown(signum, frame):  # noqa: ARG001
        worker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while worker.is_running():
        time.sleep(1)


if __name__ == "__main__":
    main()
