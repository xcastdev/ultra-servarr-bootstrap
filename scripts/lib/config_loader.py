"""Load config/config.yml, merge with environment secrets, resolve paths."""

import os
import copy
import yaml


def load_config(config_path: str, env: dict | None = None) -> dict:
    """Load YAML config and resolve secrets + paths from environment.

    Returns a fully resolved config dict with:
      - base_url: https://{user}.{server}.usbx.me
      - home_dir: /home/{user}
      - All relative paths converted to absolute
      - All api_key_secret references resolved to actual values
      - qbittorrent credentials injected
    """
    if env is None:
        env = os.environ

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    config = copy.deepcopy(raw)

    username = _require_env(env, "ULTRA_USERNAME")
    servername = _require_env(env, "ULTRA_SERVERNAME")

    config["username"] = username
    config["servername"] = servername
    config["base_url"] = f"https://{username}.{servername}.usbx.me"
    config["home_dir"] = f"/home/{username}"

    # --- qBittorrent ---
    qbit = config.get("qbittorrent", {})
    qbit["url"] = config["base_url"] + qbit.get("app_path", "/qbittorrent")
    qbit["default_save_path"] = _abs_path(
        config["home_dir"], qbit.get("default_save_path", "downloads/qbittorrent")
    )
    qbit["username"] = _require_env(env, "QBIT_USER")
    qbit["password"] = _require_env(env, "QBIT_PASS")
    config["qbittorrent"] = qbit

    # --- Instances (Sonarr, Radarr, Prowlarr, Jellyfin, Jellyseerr) ---
    instances = config.get("instances", {})
    for name, inst in instances.items():
        inst["url"] = config["base_url"] + inst.get("app_path", "")
        inst["name"] = name

        # Resolve API key from environment
        secret_name = inst.get("api_key_secret")
        if secret_name:
            inst["api_key"] = _require_env(env, secret_name)

        # Resolve relative paths to absolute
        if "root_folder" in inst:
            inst["root_folder"] = _abs_path(config["home_dir"], inst["root_folder"])

    config["instances"] = instances
    return config


def _require_env(env: dict, key: str) -> str:
    """Get a required environment variable or raise."""
    value = env.get(key)
    if not value:
        raise ValueError(f"Required environment variable {key!r} is not set")
    return value


def _abs_path(home_dir: str, relative: str) -> str:
    """Convert a home-relative path to absolute."""
    return os.path.join(home_dir, relative)
