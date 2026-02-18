"""Connectivity validation — hit each service health endpoint before mutations."""

import logging

from lib.api_client import ArrClient, QbitClient, JellyfinClient, JellyseerrClient

log = logging.getLogger(__name__)

# Health endpoints per service type
_HEALTH_ENDPOINTS = {
    "sonarr": ("arr", "api/v3/system/status"),
    "radarr": ("arr", "api/v3/system/status"),
    "prowlarr": ("arr", "api/v1/system/status"),
    "qbittorrent": ("qbit", None),  # login doubles as health check
    "jellyfin": ("jellyfin", "System/Info"),
    "jellyseerr": ("jellyseerr", "api/v1/status"),
}


def validate(config: dict, requested: set[str]) -> set[str]:
    """Check connectivity for each requested service.

    Returns the set of service names that are reachable.
    """
    reachable = set()

    for service_name in requested:
        try:
            if service_name == "qbittorrent":
                _check_qbittorrent(config)
            elif service_name in ("jellyfin",):
                _check_jellyfin(config)
            elif service_name in ("jellyseerr",):
                _check_jellyseerr(config)
            else:
                _check_arr(config, service_name)

            log.info("[validate] %s: OK", service_name)
            reachable.add(service_name)

        except Exception as exc:
            log.warning("[validate] %s: UNREACHABLE — %s", service_name, exc)

    return reachable


def _check_arr(config: dict, service_name: str):
    """Validate an Arr instance (Sonarr, Radarr, Prowlarr)."""
    inst = config["instances"][service_name]
    client = ArrClient(inst["url"], inst["api_key"])

    svc_type = inst.get("type", service_name)
    if svc_type in ("sonarr", "radarr"):
        endpoint = "api/v3/system/status"
    else:
        # prowlarr
        endpoint = "api/v1/system/status"

    client.get(endpoint)


def _check_qbittorrent(config: dict):
    """Validate qBittorrent by logging in."""
    qbit = config["qbittorrent"]
    client = QbitClient(qbit["url"], qbit["username"], qbit["password"])
    client.login()


def _check_jellyfin(config: dict):
    """Validate Jellyfin."""
    inst = config["instances"]["jellyfin"]
    client = JellyfinClient(inst["url"], inst["api_key"])
    client.get("System/Info")


def _check_jellyseerr(config: dict):
    """Validate Jellyseerr."""
    inst = config["instances"]["jellyseerr"]
    client = JellyseerrClient(inst["url"], inst["api_key"])
    client.get("api/v1/status")
