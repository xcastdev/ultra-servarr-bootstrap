"""Jellyfin configuration — library creation."""

import logging

from lib.api_client import JellyfinClient

log = logging.getLogger(__name__)

# Fallback library definitions if not specified in config
_DEFAULT_LIBRARIES = [
    {
        "name": "TV Shows",
        "collectionType": "tvshows",
        "path": "media/all/tv",
    },
    {
        "name": "TV Shows UHD",
        "collectionType": "tvshows",
        "path": "media/all/tv-uhd",
    },
    {
        "name": "Movies",
        "collectionType": "movies",
        "path": "media/all/movies",
    },
    {
        "name": "Movies UHD",
        "collectionType": "movies",
        "path": "media/all/movies-uhd",
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

    # Read library definitions from config, fall back to defaults
    libraries = inst.get("libraries", _DEFAULT_LIBRARIES)

    # Get existing virtual folders (libraries)
    existing = client.get("Library/VirtualFolders")
    existing_names = {lib["Name"] for lib in existing}

    created_any = False
    for lib in libraries:
        lib_name = lib["name"]
        lib_path = f"{home_dir}/{lib['path']}"

        if lib_name in existing_names:
            log.info("Jellyfin library already exists: %s", lib_name)
            continue

        # POST /Library/VirtualFolders
        # - name, collectionType, paths, refreshLibrary as query params
        # - LibraryOptions as JSON body
        # Defer refresh until all libraries are created.
        client.post(
            "Library/VirtualFolders",
            params={
                "name": lib_name,
                "collectionType": lib["collectionType"],
                "paths": [lib_path],
                "refreshLibrary": "false",
            },
            json={"LibraryOptions": {}},
        )
        changes.append(f"Created library: {lib_name} ({lib_path})")
        created_any = True

    # Trigger a library refresh if we created anything
    if created_any:
        client.post("Library/Refresh")
        changes.append("Triggered library refresh")

    return changes
