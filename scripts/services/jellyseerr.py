"""Jellyseerr configuration — Sonarr and Radarr server connections."""

import logging

from lib.api_client import JellyseerrClient

log = logging.getLogger(__name__)

# Quality profile names created by Recyclarr templates
_QUALITY_PROFILES = {
    "sonarr": "WEB-1080p",
    "sonarr2": "WEB-2160p",
    "radarr": "HD Bluray + WEB",
    "radarr2": "UHD Bluray + WEB",
}

# Which instances are default for standard vs 4K requests
_DEFAULT_STANDARD = {"sonarr", "radarr"}
_DEFAULT_4K = {"sonarr2", "radarr2"}


def configure_jellyseerr(
    config: dict, service_name: str, *, dry_run: bool = False
) -> list[str]:
    """Configure Jellyseerr with Sonarr and Radarr server connections.

    Returns a list of changes made.
    """
    inst = config["instances"]["jellyseerr"]
    client = JellyseerrClient(inst["url"], inst["api_key"], dry_run=dry_run)

    changes = []

    changes.extend(_configure_sonarr_servers(client, config))
    changes.extend(_configure_radarr_servers(client, config))

    return changes


def _configure_sonarr_servers(client: JellyseerrClient, config: dict) -> list[str]:
    """Add Sonarr instances to Jellyseerr."""
    changes = []
    existing = client.get("api/v1/settings/sonarr")

    sonarr_instances = {
        name: inst
        for name, inst in config["instances"].items()
        if inst.get("type") == "sonarr"
    }

    host = f"{config['username']}.{config['servername']}.usbx.me"

    for name, inst in sonarr_instances.items():
        base_url = inst.get("app_path", "")
        profile_name = _QUALITY_PROFILES.get(name, "")
        is_default = name in _DEFAULT_STANDARD
        is_4k = name in _DEFAULT_4K

        # Check if this instance already exists by matching baseUrl
        found = _find_existing_server(existing, base_url)

        # Resolve quality profile, language profile, and root folder
        profile_id, resolved_profile_name = _resolve_profile(client, inst, profile_name)
        lang_profile_id = _resolve_language_profile_id(inst)
        root_folder = inst.get("root_folder", "")

        payload = {
            "name": name.title().replace("2", " 4K"),
            "hostname": host,
            "port": 443,
            "useSsl": True,
            "apiKey": inst["api_key"],
            "baseUrl": base_url,
            "activeProfileId": profile_id,
            "activeProfileName": resolved_profile_name,
            "activeLanguageProfileId": lang_profile_id,
            "activeDirectory": root_folder,
            "isDefault": is_default,
            "is4k": is_4k,
            "enableSeasonFolders": True,
        }

        if found:
            # Update existing — id is read-only, passed via URL only
            client.put(f"api/v1/settings/sonarr/{found['id']}", json=payload)
            changes.append(f"Updated Jellyseerr Sonarr server: {name}")
        else:
            client.post("api/v1/settings/sonarr", json=payload)
            changes.append(f"Added Jellyseerr Sonarr server: {name}")

    return changes


def _configure_radarr_servers(client: JellyseerrClient, config: dict) -> list[str]:
    """Add Radarr instances to Jellyseerr."""
    changes = []
    existing = client.get("api/v1/settings/radarr")

    radarr_instances = {
        name: inst
        for name, inst in config["instances"].items()
        if inst.get("type") == "radarr"
    }

    host = f"{config['username']}.{config['servername']}.usbx.me"

    for name, inst in radarr_instances.items():
        base_url = inst.get("app_path", "")
        profile_name = _QUALITY_PROFILES.get(name, "")
        is_default = name in _DEFAULT_STANDARD
        is_4k = name in _DEFAULT_4K

        found = _find_existing_server(existing, base_url)

        profile_id, resolved_profile_name = _resolve_profile(client, inst, profile_name)
        root_folder = inst.get("root_folder", "")

        payload = {
            "name": name.title().replace("2", " 4K"),
            "hostname": host,
            "port": 443,
            "useSsl": True,
            "apiKey": inst["api_key"],
            "baseUrl": base_url,
            "activeProfileId": profile_id,
            "activeProfileName": resolved_profile_name,
            "activeDirectory": root_folder,
            "minimumAvailability": "released",
            "isDefault": is_default,
            "is4k": is_4k,
        }

        if found:
            # Update existing — id is read-only, passed via URL only
            client.put(f"api/v1/settings/radarr/{found['id']}", json=payload)
            changes.append(f"Updated Jellyseerr Radarr server: {name}")
        else:
            client.post("api/v1/settings/radarr", json=payload)
            changes.append(f"Added Jellyseerr Radarr server: {name}")

    return changes


def _find_existing_server(existing: list, base_url: str) -> dict | None:
    """Find an existing server entry by baseUrl."""
    for server in existing:
        if server.get("baseUrl") == base_url:
            return server
    return None


def _resolve_language_profile_id(inst: dict) -> int:
    """Resolve a language profile ID from a Sonarr instance.

    Sonarr v3 has a separate languageprofile endpoint.
    Sonarr v4 merged language into quality profiles — the endpoint returns
    empty or 404, so we fall back to ID 1 (usually 'English' or 'Any').
    """
    try:
        from lib.api_client import ArrClient

        arr_client = ArrClient(inst["url"], inst["api_key"])
        profiles = arr_client.get("api/v3/languageprofile")
        if profiles:
            # Prefer 'English', fall back to first available
            for p in profiles:
                if p.get("name", "").lower() == "english":
                    return p["id"]
            return profiles[0]["id"]
    except Exception as exc:
        log.warning("Could not fetch language profiles from %s: %s", inst["name"], exc)

    # Sonarr v4 or error — use default ID 1
    return 1


def _resolve_profile(
    client: JellyseerrClient, inst: dict, profile_name: str
) -> tuple[int, str]:
    """Resolve a quality profile name to its ID and name via the Arr API.

    Jellyseerr requires both activeProfileId and activeProfileName.
    If the profile doesn't exist yet (Recyclarr hasn't run), fall back
    to the first available profile.

    Returns (profile_id, profile_name).
    """
    if not profile_name:
        return 0, ""

    try:
        from lib.api_client import ArrClient

        arr_client = ArrClient(inst["url"], inst["api_key"])
        profiles = arr_client.get("api/v3/qualityprofile")

        for profile in profiles:
            if profile["name"] == profile_name:
                return profile["id"], profile["name"]

        # Profile not found — Recyclarr may not have run yet
        log.warning(
            "Quality profile %r not found on %s — using first available",
            profile_name,
            inst["name"],
        )
        if profiles:
            return profiles[0]["id"], profiles[0]["name"]
    except Exception as exc:
        log.warning("Could not resolve profile %r: %s", profile_name, exc)

    return 0, ""
