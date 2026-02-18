"""Radarr configuration — root folders, download client, media management, tags.

Shares the same logic as Sonarr but uses movieCategory instead of tvCategory.
"""

import logging

from lib.api_client import ArrClient

log = logging.getLogger(__name__)


def configure_radarr(
    config: dict, service_name: str, *, dry_run: bool = False
) -> list[str]:
    """Configure a Radarr instance (works for both radarr and radarr2).

    Returns a list of changes made.
    """
    inst = config["instances"][service_name]
    client = ArrClient(inst["url"], inst["api_key"], dry_run=dry_run)

    changes = []

    changes.extend(_ensure_root_folder(client, inst))
    changes.extend(_ensure_download_client(client, config, inst))
    changes.extend(_set_media_management(client, config))
    changes.extend(_ensure_tags(client, config, service_name))

    return changes


def _ensure_root_folder(client: ArrClient, inst: dict) -> list[str]:
    """Ensure the root folder exists."""
    changes = []
    folders = client.get("api/v3/rootfolder")
    desired = inst["root_folder"]

    existing_paths = [f["path"] for f in folders]
    if desired not in existing_paths:
        client.post("api/v3/rootfolder", json={"path": desired})
        changes.append(f"Added root folder: {desired}")
    else:
        log.info("Root folder already exists: %s", desired)

    return changes


def _ensure_download_client(client: ArrClient, config: dict, inst: dict) -> list[str]:
    """Ensure qBittorrent download client is configured with movieCategory."""
    changes = []
    clients = client.get("api/v3/downloadclient")
    qbit_cfg = config["qbittorrent"]

    host = f"{config['username']}.{config['servername']}.usbx.me"
    expected_fields = {
        "host": host,
        "port": 443,
        "urlBase": "/qbittorrent",
        "username": qbit_cfg["username"],
        "password": qbit_cfg["password"],
        "movieCategory": inst.get("category", ""),
        "useSsl": True,
    }

    # Look for existing qBittorrent client
    existing = None
    for dc in clients:
        if dc.get("implementation") == "QBittorrent":
            existing = dc
            break

    if existing is None:
        payload = _build_download_client_payload(expected_fields, inst)
        client.post("api/v3/downloadclient", json=payload)
        changes.append("Added qBittorrent download client")
    else:
        current_fields = {f["name"]: f["value"] for f in existing.get("fields", [])}
        needs_update = False
        for key, val in expected_fields.items():
            if key == "password":
                continue
            if current_fields.get(key) != val:
                needs_update = True
                break

        if needs_update:
            payload = _build_download_client_payload(expected_fields, inst)
            payload["id"] = existing["id"]
            client.put(f"api/v3/downloadclient/{existing['id']}", json=payload)
            changes.append("Updated qBittorrent download client settings")
        else:
            log.info("Download client already configured correctly")

    return changes


def _build_download_client_payload(fields: dict, inst: dict) -> dict:
    """Build the download client JSON payload for Radarr (uses movieCategory)."""
    return {
        "name": "qBittorrent",
        "implementation": "QBittorrent",
        "configContract": "QBittorrentSettings",
        "enable": True,
        "protocol": "torrent",
        "fields": [
            {"name": "host", "value": fields["host"]},
            {"name": "port", "value": fields["port"]},
            {"name": "urlBase", "value": fields["urlBase"]},
            {"name": "username", "value": fields["username"]},
            {"name": "password", "value": fields["password"]},
            {"name": "movieCategory", "value": fields["movieCategory"]},
            {"name": "useSsl", "value": fields["useSsl"]},
        ],
    }


def _set_media_management(client: ArrClient, config: dict) -> list[str]:
    """Check and update media management settings."""
    changes = []
    current = client.get("api/v3/config/mediamanagement")
    mm_cfg = config.get("media_management", {})

    updates = {}

    desired_hardlinks = not mm_cfg.get("hardlinks", True)
    if current.get("hardlinksCopy") != desired_hardlinks:
        updates["hardlinksCopy"] = desired_hardlinks
        changes.append(
            f"Set hardlinks: {'enabled' if not desired_hardlinks else 'disabled'}"
        )

    desired_analyze = mm_cfg.get("analyze_video", False)
    if current.get("enableMediaInfo") != desired_analyze:
        updates["enableMediaInfo"] = desired_analyze
        changes.append(f"Set analyze video: {desired_analyze}")

    desired_propers = mm_cfg.get("propers_and_repacks", "doNotPrefer")
    if current.get("downloadPropersAndRepacks") != desired_propers:
        updates["downloadPropersAndRepacks"] = desired_propers
        changes.append(f"Set propers/repacks: {desired_propers}")

    if updates:
        payload = {**current, **updates}
        client.put("api/v3/config/mediamanagement", json=payload)
    else:
        log.info("Media management settings already correct")

    return changes


def _ensure_tags(client: ArrClient, config: dict, service_name: str) -> list[str]:
    """Ensure configured tags exist."""
    changes = []
    desired_tags = config.get("tags", {}).get(service_name, [])
    if not desired_tags:
        return changes

    existing_tags = client.get("api/v3/tag")
    existing_names = {t["label"].lower() for t in existing_tags}

    for tag in desired_tags:
        if tag.lower() not in existing_names:
            client.post("api/v3/tag", json={"label": tag})
            changes.append(f"Created tag: {tag}")
        else:
            log.info("Tag already exists: %s", tag)

    return changes
