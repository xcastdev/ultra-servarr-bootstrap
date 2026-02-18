"""Prowlarr configuration — app connections to all Arr instances."""

import logging

from lib.api_client import ArrClient

log = logging.getLogger(__name__)

# Arr instance types and their Prowlarr implementation/contract names
_APP_TYPES = {
    "sonarr": {
        "implementation": "Sonarr",
        "configContract": "SonarrSettings",
    },
    "radarr": {
        "implementation": "Radarr",
        "configContract": "RadarrSettings",
    },
}


def configure_prowlarr(
    config: dict, service_name: str, *, dry_run: bool = False
) -> list[str]:
    """Connect Prowlarr to all configured Arr instances.

    Returns a list of changes made.
    """
    prowlarr_inst = config["instances"]["prowlarr"]
    client = ArrClient(prowlarr_inst["url"], prowlarr_inst["api_key"], dry_run=dry_run)

    changes = []

    # Get existing applications
    existing_apps = client.get("api/v1/applications")
    existing_by_url = {}
    for app in existing_apps:
        fields = {f["name"]: f["value"] for f in app.get("fields", [])}
        base_url = fields.get("baseUrl", "")
        if base_url:
            existing_by_url[base_url] = app

    # Prowlarr's own URL for the prowlarrUrl field
    prowlarr_url = prowlarr_inst["url"]

    # Process each Arr instance
    arr_instances = {
        name: inst
        for name, inst in config["instances"].items()
        if inst.get("type") in ("sonarr", "radarr")
    }

    for name, inst in arr_instances.items():
        app_type = inst["type"]
        type_info = _APP_TYPES[app_type]
        arr_url = inst["url"]

        # Build expected field values
        expected_fields = {
            "baseUrl": arr_url,
            "apiKey": inst["api_key"],
            "prowlarrUrl": prowlarr_url,
        }

        display_name = name.replace("2", " 4K").title()

        if arr_url in existing_by_url:
            existing = existing_by_url[arr_url]
            current_fields = {f["name"]: f["value"] for f in existing.get("fields", [])}

            needs_update = False
            for key, val in expected_fields.items():
                if key == "apiKey":
                    continue  # API keys not returned
                if current_fields.get(key) != val:
                    needs_update = True
                    break

            if needs_update:
                payload = _build_app_payload(display_name, type_info, expected_fields)
                payload["id"] = existing["id"]
                client.put(f"api/v1/applications/{existing['id']}", json=payload)
                changes.append(f"Updated Prowlarr app: {display_name}")
            else:
                log.info("Prowlarr app already configured: %s", display_name)
        else:
            payload = _build_app_payload(display_name, type_info, expected_fields)
            client.post("api/v1/applications", json=payload)
            changes.append(f"Added Prowlarr app: {display_name}")

    # Trigger indexer sync after all apps are configured
    if changes:
        client.post("api/v1/command", json={"name": "ApplicationIndexerSync"})
        changes.append("Triggered ApplicationIndexerSync")

    return changes


def _build_app_payload(name: str, type_info: dict, fields: dict) -> dict:
    """Build the Prowlarr application payload."""
    return {
        "name": name,
        "syncLevel": "fullSync",
        "implementation": type_info["implementation"],
        "configContract": type_info["configContract"],
        "fields": [
            {"name": "baseUrl", "value": fields["baseUrl"]},
            {"name": "apiKey", "value": fields["apiKey"]},
            {"name": "prowlarrUrl", "value": fields["prowlarrUrl"]},
        ],
    }
