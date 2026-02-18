"""Structured summary logger for the setup pipeline."""

import logging
import sys
from enum import Enum

log = logging.getLogger(__name__)


class Status(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class SummaryLogger:
    """Track per-service results and print a final summary."""

    def __init__(self):
        self._services: dict[str, dict] = {}

    def _ensure(self, service: str):
        if service not in self._services:
            self._services[service] = {
                "status": Status.PENDING,
                "changes": [],
                "errors": [],
            }

    def log_change(self, service: str, message: str):
        """Record a successful change."""
        self._ensure(service)
        self._services[service]["changes"].append(message)
        log.info("[%s] %s", service, message)

    def log_skip(self, service: str, reason: str):
        """Record that a service was skipped."""
        self._ensure(service)
        self._services[service]["status"] = Status.SKIPPED
        self._services[service]["changes"].append(f"Skipped: {reason}")
        log.info("[%s] Skipped: %s", service, reason)

    def log_error(self, service: str, error: str):
        """Record an error for a service."""
        self._ensure(service)
        self._services[service]["errors"].append(error)
        log.error("[%s] ERROR: %s", service, error)

    def mark_in_progress(self, service: str):
        self._ensure(service)
        self._services[service]["status"] = Status.IN_PROGRESS

    def mark_success(self, service: str, changes: list[str] | None = None):
        self._ensure(service)
        self._services[service]["status"] = Status.SUCCESS
        if changes:
            self._services[service]["changes"].extend(changes)

    def mark_failed(self, service: str, error: str):
        self._ensure(service)
        self._services[service]["status"] = Status.FAILED
        self._services[service]["errors"].append(error)
        log.error("[%s] FAILED: %s", service, error)

    def has_failures(self) -> bool:
        return any(s["status"] == Status.FAILED for s in self._services.values())

    def print_summary(self):
        """Print a formatted summary suitable for GitHub Actions logs."""
        counts = {s: 0 for s in Status}
        for info in self._services.values():
            counts[info["status"]] += 1

        print("\n" + "=" * 60)
        print("  SETUP SUMMARY")
        print("=" * 60)

        for name, info in self._services.items():
            status = info["status"]
            icon = {
                Status.SUCCESS: "OK",
                Status.FAILED: "FAIL",
                Status.SKIPPED: "SKIP",
                Status.IN_PROGRESS: "...",
                Status.PENDING: "---",
            }.get(status, "???")

            print(f"\n  [{icon}] {name}")
            for change in info["changes"]:
                print(f"        + {change}")
            for error in info["errors"]:
                print(f"        ! {error}")

        print("\n" + "-" * 60)
        parts = []
        if counts[Status.SUCCESS]:
            parts.append(f"{counts[Status.SUCCESS]} succeeded")
        if counts[Status.FAILED]:
            parts.append(f"{counts[Status.FAILED]} failed")
        if counts[Status.SKIPPED]:
            parts.append(f"{counts[Status.SKIPPED]} skipped")
        print(f"  Result: {', '.join(parts) or 'nothing to do'}")

        if self.has_failures():
            failed = [
                n for n, i in self._services.items() if i["status"] == Status.FAILED
            ]
            print(f"  Re-run with: --services {','.join(failed)}")

        print("=" * 60 + "\n")
        sys.stdout.flush()
