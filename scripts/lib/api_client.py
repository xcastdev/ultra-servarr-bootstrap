"""HTTP clients for all Servarr services with retry, dry-run, and auth."""

import time
import logging

import requests

log = logging.getLogger(__name__)

# Retry settings
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds


class _BaseClient:
    """Shared retry and dry-run logic."""

    def __init__(self, base_url: str, *, dry_run: bool = False):
        self.base_url = base_url.rstrip("/")
        self.dry_run = dry_run
        self.session = requests.Session()

    # --- internal helpers ---

    def _headers(self) -> dict:
        """Override in subclasses to inject auth headers."""
        return {}

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Execute an HTTP request with retry on 5xx / connection errors."""
        url = self._url(path)
        headers = {**self._headers(), **kwargs.pop("headers", {})}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.request(
                    method, url, headers=headers, timeout=30, **kwargs
                )
                if resp.status_code >= 500:
                    raise requests.exceptions.HTTPError(
                        f"{resp.status_code} Server Error", response=resp
                    )
                resp.raise_for_status()
                return resp
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError,
            ) as exc:
                if attempt == MAX_RETRIES:
                    raise
                wait = BACKOFF_BASE**attempt
                log.warning(
                    "Attempt %d/%d failed for %s %s: %s — retrying in %ds",
                    attempt,
                    MAX_RETRIES,
                    method.upper(),
                    url,
                    exc,
                    wait,
                )
                time.sleep(wait)
        # unreachable, but keeps type checkers happy
        raise RuntimeError("Exhausted retries")

    # --- public API ---

    def get(self, path: str, **kwargs):
        """GET always allowed (even in dry-run)."""
        resp = self._request("GET", path, **kwargs)
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text

    def post(self, path: str, **kwargs):
        """POST — skipped in dry-run for mutations."""
        if self.dry_run:
            log.info("[DRY-RUN] Would POST %s", self._url(path))
            return None
        resp = self._request("POST", path, **kwargs)
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text

    def put(self, path: str, **kwargs):
        """PUT — skipped in dry-run for mutations."""
        if self.dry_run:
            log.info("[DRY-RUN] Would PUT %s", self._url(path))
            return None
        resp = self._request("PUT", path, **kwargs)
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text

    def delete(self, path: str, **kwargs):
        """DELETE — skipped in dry-run."""
        if self.dry_run:
            log.info("[DRY-RUN] Would DELETE %s", self._url(path))
            return None
        resp = self._request("DELETE", path, **kwargs)
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text


class ArrClient(_BaseClient):
    """Client for Sonarr, Radarr, and Prowlarr (X-Api-Key auth)."""

    def __init__(self, base_url: str, api_key: str, *, dry_run: bool = False):
        super().__init__(base_url, dry_run=dry_run)
        self.api_key = api_key

    def _headers(self) -> dict:
        return {"X-Api-Key": self.api_key}


class QbitClient(_BaseClient):
    """Client for qBittorrent (session cookie auth).

    Authenticates via POST /api/v2/auth/login, then reuses the SID cookie.
    """

    def __init__(
        self, base_url: str, username: str, password: str, *, dry_run: bool = False
    ):
        super().__init__(base_url, dry_run=dry_run)
        self._qbit_username = username
        self._qbit_password = password
        self._authenticated = False

    def login(self):
        """Authenticate and store SID cookie in the session."""
        resp = self._request(
            "POST",
            "api/v2/auth/login",
            data={"username": self._qbit_username, "password": self._qbit_password},
        )
        body = resp.text if isinstance(resp, requests.Response) else resp
        if body != "Ok.":
            raise RuntimeError(f"qBittorrent login failed: {body}")
        self._authenticated = True
        log.info("qBittorrent: authenticated successfully")

    def get(self, path: str, **kwargs):
        if not self._authenticated:
            self.login()
        return super().get(path, **kwargs)

    def post(self, path: str, **kwargs):
        if not self._authenticated and path != "api/v2/auth/login":
            self.login()
        return super().post(path, **kwargs)


class JellyfinClient(_BaseClient):
    """Client for Jellyfin (MediaBrowser token auth)."""

    def __init__(self, base_url: str, api_key: str, *, dry_run: bool = False):
        super().__init__(base_url, dry_run=dry_run)
        self.api_key = api_key

    def _headers(self) -> dict:
        return {"Authorization": f'MediaBrowser Token="{self.api_key}"'}


class JellyseerrClient(_BaseClient):
    """Client for Jellyseerr (X-Api-Key auth)."""

    def __init__(self, base_url: str, api_key: str, *, dry_run: bool = False):
        super().__init__(base_url, dry_run=dry_run)
        self.api_key = api_key

    def _headers(self) -> dict:
        return {"X-Api-Key": self.api_key}
