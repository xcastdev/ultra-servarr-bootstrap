"""Jellyfin configuration — library creation."""

import logging
import urllib.parse

from lib.api_client import JellyfinClient

log = logging.getLogger(__name__)

# Libraries to create, keyed by display name
_LIBRARIES = [
    {
        "name": "TV Shows",
        "collectionType": "tvshows",
        "path_key": "media/tv",
    },
    {
        "name": "TV Shows UHD",
        "collectionType": "tvshows",
        "path_key": "media/tv-uhd",
    },
    {
        "name": "Movies",
        "collectionType": "movies",
        "path_key": "media/movies",
    },
    {
        "name": "Movies UHD",
        "collectionType": "movies",
        "path_key": "media/movies-uhd",
    },
]


def configure_jellyfin(
    config: dict, service_name: str, *, dry_run: bool = False
) -> list[str]:
    """Create Jellyfin libraries for all media folders.

    Returns a list of changes made.
    """
    inst = config["instances"]["jellyfin"]
    client = JellyfinClient(inst["url"], inst["api_key"], dry_run=dry_run)

    changes = []
    home_dir = config["home_dir"]

    # Get existing virtual folders (libraries)
    existing = client.get("Library/VirtualFolders")
    existing_names = {lib["Name"] for lib in existing}

    created_any = False
    for lib in _LIBRARIES:
        lib_name = lib["name"]
        lib_path = f"{home_dir}/{lib['path_key']}"

        if lib_name in existing_names:
            log.info("Jellyfin library already exists: %s", lib_name)
            continue

        # POST /Library/VirtualFolders?name=...&collectionType=...&paths=...&refreshLibrary=true
        # Pass path via query param (most reliable across Jellyfin versions)
        params = urllib.parse.urlencode(
            [
                ("name", lib_name),
                ("collectionType", lib["collectionType"]),
                ("paths", lib_path),
                ("refreshLibrary", "true"),
            ]
        )
        client.post(
            f"Library/VirtualFolders?{params}",
            json={"LibraryOptions": {}},
            headers={"Content-Type": "application/json"},
        )
        changes.append(f"Created library: {lib_name} ({lib_path})")
        created_any = True

    # Trigger a library refresh if we created anything
    if created_any:
        client.post("Library/Refresh")
        changes.append("Triggered library refresh")

    return changes
