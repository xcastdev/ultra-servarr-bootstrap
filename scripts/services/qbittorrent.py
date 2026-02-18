"""qBittorrent configuration — preferences and categories."""

import logging

from lib.api_client import QbitClient

log = logging.getLogger(__name__)

# Map config keys to qBittorrent API preference keys
_PREF_MAP = {
    "torrent_management_mode": "auto_tmm_enabled",
    "torrent_content_layout": "torrent_content_layout",
    "relocate_on_category_change": "torrent_changed_tmm_enabled",
    "relocate_on_default_save_path_change": "save_path_changed_tmm_enabled",
}

# Config values that need translation to API values
_VALUE_MAP = {
    "torrent_management_mode": {"automatic": True, "manual": False},
}


def configure_qbittorrent(
    config: dict, service_name: str, *, dry_run: bool = False
) -> list[str]:
    """Configure qBittorrent preferences and categories.

    Returns a list of changes made.
    """
    qbit_cfg = config["qbittorrent"]
    client = QbitClient(
        qbit_cfg["url"], qbit_cfg["username"], qbit_cfg["password"], dry_run=dry_run
    )
    client.login()

    changes = []

    # --- Preferences ---
    changes.extend(_set_preferences(client, qbit_cfg))

    # --- Categories ---
    changes.extend(_set_categories(client, qbit_cfg))

    return changes


def _set_preferences(client: QbitClient, qbit_cfg: dict) -> list[str]:
    """Check and update global qBittorrent preferences."""
    changes = []
    current = client.get("api/v2/app/preferences")
    desired_prefs = qbit_cfg.get("preferences", {})
    updates = {}

    # Default save path
    desired_save_path = qbit_cfg["default_save_path"]
    if current.get("save_path") != desired_save_path:
        updates["save_path"] = desired_save_path
        changes.append(f"Set default save path: {desired_save_path}")

    # Mapped preferences
    for config_key, api_key in _PREF_MAP.items():
        if config_key not in desired_prefs:
            continue

        desired_value = desired_prefs[config_key]
        # Translate config values to API values if needed
        if config_key in _VALUE_MAP:
            desired_value = _VALUE_MAP[config_key].get(desired_value, desired_value)

        if current.get(api_key) != desired_value:
            updates[api_key] = desired_value
            changes.append(f"Set {api_key}: {desired_value}")

    if updates:
        import json

        client.post("api/v2/app/setPreferences", data={"json": json.dumps(updates)})
    else:
        log.info("qBittorrent: all preferences already correct")

    return changes


def _set_categories(client: QbitClient, qbit_cfg: dict) -> list[str]:
    """Ensure all configured categories exist with correct save paths."""
    changes = []
    current_cats = client.get("api/v2/torrents/categories")
    desired_cats = qbit_cfg.get("categories", {})

    for cat_name, cat_cfg in desired_cats.items():
        desired_path = cat_cfg.get("save_path", cat_name)

        if cat_name not in current_cats:
            # Category doesn't exist — create it
            client.post(
                "api/v2/torrents/createCategory",
                data={"category": cat_name, "savePath": desired_path},
            )
            changes.append(f"Created category: {cat_name} (path: {desired_path})")

        elif current_cats[cat_name].get("savePath") != desired_path:
            # Category exists but wrong path — update it
            client.post(
                "api/v2/torrents/editCategory",
                data={"category": cat_name, "savePath": desired_path},
            )
            changes.append(f"Updated category {cat_name} path: {desired_path}")

        else:
            log.info("qBittorrent: category %s already correct", cat_name)

    return changes
