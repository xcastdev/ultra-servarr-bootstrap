#!/usr/bin/env python3
"""Main orchestrator — configures the Servarr stack in dependency order."""

import argparse
import logging
import os
import sys

# Ensure scripts/ is on the import path so lib/ and services/ resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.config_loader import load_config
from lib.logger import SummaryLogger
from validate import validate

from services.qbittorrent import configure_qbittorrent
from services.sonarr import configure_sonarr
from services.radarr import configure_radarr
from services.prowlarr import configure_prowlarr
from services.jellyfin import configure_jellyfin
from services.jellyseerr import configure_jellyseerr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

# All known services in dependency order
ALL_SERVICES = [
    "qbittorrent",
    "sonarr",
    "sonarr2",
    "radarr",
    "radarr2",
    "prowlarr",
    "jellyfin",
    "jellyseerr",
]

# Map service names to their configure functions
# Sonarr/Sonarr2 share configure_sonarr; Radarr/Radarr2 share configure_radarr
_CONFIGURE_FN = {
    "qbittorrent": configure_qbittorrent,
    "sonarr": configure_sonarr,
    "sonarr2": configure_sonarr,
    "radarr": configure_radarr,
    "radarr2": configure_radarr,
    "prowlarr": configure_prowlarr,
    "jellyfin": configure_jellyfin,
    "jellyseerr": configure_jellyseerr,
}


def parse_services(raw: str) -> set[str]:
    """Parse the --services argument into a set of service names."""
    if raw.strip().lower() == "all":
        return set(ALL_SERVICES)

    requested = set()
    for part in raw.split(","):
        name = part.strip().lower()
        if name and name in ALL_SERVICES:
            requested.add(name)
        elif name:
            log.warning("Unknown service %r — ignoring", name)
    return requested


def main():
    parser = argparse.ArgumentParser(description="Ultra.cc Servarr Bootstrap")
    parser.add_argument(
        "--services",
        default="all",
        help='Comma-separated list of services to configure, or "all"',
    )
    parser.add_argument(
        "--dry-run",
        default="false",
        help="Preview changes without applying (true/false)",
    )
    parser.add_argument(
        "--config",
        default="config/config.yml",
        help="Path to config file",
    )
    args = parser.parse_args()

    dry_run = args.dry_run.lower() in ("true", "1", "yes")
    if dry_run:
        log.info("=== DRY-RUN MODE — no mutations will be applied ===")

    # Load and resolve configuration
    config = load_config(args.config, env=os.environ)
    requested = parse_services(args.services)
    summary = SummaryLogger()

    log.info("Requested services: %s", ", ".join(sorted(requested)))

    # Validate connectivity for requested services
    reachable = validate(config, requested)
    log.info("Reachable services: %s", ", ".join(sorted(reachable)))

    # Execute in dependency order
    for service_name in ALL_SERVICES:
        if service_name not in requested:
            continue

        if service_name not in reachable:
            summary.log_skip(service_name, "unreachable")
            continue

        func = _CONFIGURE_FN.get(service_name)
        if not func:
            summary.log_skip(service_name, "no configure function")
            continue

        try:
            summary.mark_in_progress(service_name)
            changes = func(config, service_name, dry_run=dry_run)
            summary.mark_success(service_name, changes)
        except Exception as exc:
            log.exception("Error configuring %s", service_name)
            summary.mark_failed(service_name, str(exc))

    summary.print_summary()
    sys.exit(1 if summary.has_failures() else 0)


if __name__ == "__main__":
    main()
