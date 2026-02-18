# Ultra.cc Servarr Bootstrap

Automated post-install configuration for a dual HD/4K Servarr media stack on [Ultra.cc](https://ultra.cc). Runs entirely from GitHub Actions -- no SSH, no self-hosted runners.

## What It Does

Two GitHub Actions workflows configure your full stack via each service's API:

| Service      | What Gets Configured                                           |
| ------------ | -------------------------------------------------------------- |
| qBittorrent  | Save path, automatic torrent management, 4 download categories |
| Sonarr (x2)  | Root folder, qBit download client, media management, tags      |
| Radarr (x2)  | Root folder, qBit download client, media management, tags      |
| Prowlarr     | App connections to all 4 Arr instances, indexer sync            |
| Jellyfin     | 4 media libraries (TV, TV UHD, Movies, Movies UHD)             |
| Jellyseerr   | 2 Sonarr + 2 Radarr servers with default/4K assignments        |
| Recyclarr    | Quality profiles and custom formats from TRaSH Guides          |

Every operation is idempotent. Running the workflow again skips anything already configured correctly.

## Instance Layout

| Instance | Purpose       | qBit Category | Root Folder      |
| -------- | ------------- | ------------- | ---------------- |
| Sonarr   | TV Shows (HD) | `tv-hd`       | `~/media/tv`     |
| Sonarr2  | TV Shows (4K) | `tv-uhd`      | `~/media/tv-uhd` |
| Radarr   | Movies (HD)   | `movies-hd`   | `~/media/movies` |
| Radarr2  | Movies (4K)   | `movies-uhd`  | `~/media/movies-uhd` |

Anime goes into the TV libraries. No separate instance needed.

---

## Prerequisites

Complete these steps before running any workflow.

### 1. Install Apps on Ultra.cc

Install all of the following through the Ultra.cc control panel:

- qBittorrent
- Sonarr + Sonarr2
- Radarr + Radarr2
- Prowlarr
- Jellyfin
- Jellyseerr

### 2. Complete Jellyfin Initial Wizard

Open `https://{username}.{servername}.usbx.me/jellyfin` and walk through the first-time setup:

1. Create an admin user (username + password)
2. Set preferred language and region
3. Skip adding media libraries (the automation handles this)
4. Finish the wizard

Then create an API key:

1. Go to **Administration > Dashboard > Advanced > API Keys**
2. Click **+** to create a new key
3. Save the key for the secrets step below

### 3. Complete Jellyseerr Initial Wizard

Open `https://{username}.{servername}.usbx.me/jellyseerr` and walk through setup:

1. Select **Jellyfin** as the media server type
2. Enter the Jellyfin connection details:
   - Hostname: `{username}.{servername}.usbx.me`
   - Port: `443`
   - SSL: **on**
   - URL Base: `/jellyfin`
3. Sign in with your Jellyfin admin credentials
4. Sync and enable libraries
5. Skip the Sonarr/Radarr setup page (the automation handles this)
6. Finish the wizard
7. Go to **Settings > General** and note the API key

### 4. Collect API Keys

| App         | Where to Find It                                      |
| ----------- | ----------------------------------------------------- |
| Sonarr      | Settings > General > Security > API Key               |
| Sonarr2     | Settings > General > Security > API Key               |
| Radarr      | Settings > General > Security > API Key               |
| Radarr2     | Settings > General > Security > API Key               |
| Prowlarr    | Settings > General > Security > API Key               |
| qBittorrent | Username/password from the Ultra.cc control panel     |
| Jellyfin    | Administration > Dashboard > Advanced > API Keys      |
| Jellyseerr  | Settings > General > API Key                          |

### 5. Store Secrets in GitHub

Secrets must be stored as **environment secrets** under an environment named **`ultra-prod`**. Repository-level secrets will not work because the workflows reference this specific environment.

1. Go to **Settings > Environments** and click **New environment**
2. Name it **`ultra-prod`** and click **Configure environment**
3. Under **Environment secrets**, click **Add secret** and create each one:

| Secret               | Value                                    |
| -------------------- | ---------------------------------------- |
| `ULTRA_USERNAME`     | Your Ultra.cc username                   |
| `ULTRA_SERVERNAME`   | Your Ultra.cc server name (e.g. `lw902`) |
| `SONARR_API_KEY`     | Sonarr API key                           |
| `SONARR2_API_KEY`    | Sonarr2 API key                          |
| `RADARR_API_KEY`     | Radarr API key                           |
| `RADARR2_API_KEY`    | Radarr2 API key                          |
| `PROWLARR_API_KEY`   | Prowlarr API key                         |
| `QBIT_USER`          | qBittorrent Web UI username              |
| `QBIT_PASS`          | qBittorrent Web UI password              |
| `JELLYFIN_API_KEY`   | Jellyfin API key                         |
| `JELLYSEERR_API_KEY` | Jellyseerr API key                       |

---

## First-Time Setup

Run the workflows in this order. All three steps are required on first setup.

### Step 1: Run the Setup Workflow

1. Go to **Actions > Setup Servarr Stack**
2. Click **Run workflow**
3. Leave services as `all` and dry_run as `false`
4. Click **Run workflow**

This configures qBittorrent, all Arr instances, Prowlarr, Jellyfin, and Jellyseerr.

### Step 2: Run the Recyclarr Sync Workflow

1. Go to **Actions > Recyclarr Sync**
2. Click **Run workflow**

This creates the quality profiles and custom formats on each Arr instance:

| Instance | Profile Created      |
| -------- | -------------------- |
| Sonarr   | WEB-1080p            |
| Sonarr2  | WEB-2160p            |
| Radarr   | HD Bluray + WEB      |
| Radarr2  | UHD Bluray + WEB     |

### Step 3: Re-run Setup for Jellyseerr

1. Go to **Actions > Setup Servarr Stack**
2. Click **Run workflow**
3. Set services to `jellyseerr`
4. Click **Run workflow**

This assigns the quality profiles that Recyclarr just created to the Jellyseerr server connections. Without this step, Jellyseerr would fall back to whichever profile happened to exist first.

> On subsequent runs, the profiles already exist and this extra step is not needed. Just run Setup and Recyclarr Sync in either order.

---

## Workflows

### Setup Servarr Stack

**File:** `.github/workflows/setup.yml`
**Trigger:** Manual (`workflow_dispatch`)

| Input      | Type    | Default | Description                               |
| ---------- | ------- | ------- | ----------------------------------------- |
| `services` | string  | `all`   | Comma-separated list of services, or `all`|
| `dry_run`  | boolean | `false` | Preview changes without applying them     |

Valid service names: `qbittorrent`, `sonarr`, `sonarr2`, `radarr`, `radarr2`, `prowlarr`, `jellyfin`, `jellyseerr`.

### Recyclarr Sync

**File:** `.github/workflows/recyclarr-sync.yml`
**Trigger:** Manual (`workflow_dispatch`)

Downloads the Recyclarr binary, builds service URLs from secrets, and syncs quality profiles + custom formats to all four Arr instances. Run this whenever you change `config/recyclarr.yml`.

---

## Dry-Run Mode

Set `dry_run` to `true` when running the Setup workflow to preview what would change without modifying anything. In this mode:

- All connectivity checks and GET requests run normally
- All mutations (POST/PUT/DELETE) are logged but skipped
- The summary shows what *would have* changed

Useful for verifying secrets are correct and services are reachable before committing to changes.

---

## Selective Retry

If a service fails, re-run only the failed services instead of the full pipeline. The summary output tells you exactly what to pass:

```
============================================================
  SETUP SUMMARY
============================================================

  [OK] qbittorrent
  [OK] sonarr
  [FAIL] sonarr2
        ! ConnectionError: timeout
  [OK] radarr
  [OK] radarr2
  [OK] prowlarr
  [OK] jellyfin
  [SKIP] jellyseerr
        + Skipped: unreachable

------------------------------------------------------------
  Result: 5 succeeded, 1 failed, 1 skipped
  Re-run with: --services sonarr2
============================================================
```

To retry, run the Setup workflow with `services` set to `sonarr2,jellyseerr`.

---

## Folder Structure

All paths live under `/home/{ULTRA_USERNAME}` on the same filesystem, which is required for hardlinks to work.

```
downloads/
  qbittorrent/              # qBit default save path
    tv-hd/                  # Sonarr HD downloads
    tv-uhd/                 # Sonarr2 4K downloads
    movies-hd/              # Radarr HD downloads
    movies-uhd/             # Radarr2 4K downloads
media/
  tv/                       # Sonarr root folder (HD TV)
  tv-uhd/                   # Sonarr2 root folder (4K TV)
  movies/                   # Radarr root folder (HD Movies)
  movies-uhd/               # Radarr2 root folder (4K Movies)
```

Torrents download in-place and seed from the same location. No incomplete/completed split, per [TRaSH Guides](https://trash-guides.info/) recommendation.

---

## Configuration

### config/config.yml

Non-sensitive settings: paths, categories, instance definitions, media management preferences, and tags. Paths in this file are relative to `/home/{ULTRA_USERNAME}` and get resolved to absolute paths at runtime.

The `api_key_secret` field on each instance is the *name* of the GitHub Secret that holds the actual key, not the key itself.

### config/recyclarr.yml

Quality profile definitions using Recyclarr's `!env_var` syntax to read URLs and API keys from environment variables. The workflow injects these at runtime from GitHub Secrets.

**Optimizations applied:**

| Feature                    | Purpose                                              |
| -------------------------- | ---------------------------------------------------- |
| `reset_unmatched_scores`   | Prevents stale CF score drift from manual changes    |
| `delete_old_custom_formats`| Keeps instances clean when CFs are removed from guides|
| Safety CFs                 | Blocks bad dual groups, no-RlsGroup, obfuscated, retags, scene at -10000 |
| DV (w/o HDR fallback)      | Blocked on 4K -- prevents purple/green on incompatible devices |
| SDR on 4K                  | Blocked -- no point grabbing SDR at 4K resolution    |
| Upscaled on Radarr 4K     | Blocked -- prevents fake 4K from HD sources          |
| IMAX / IMAX Enhanced       | Preferred at +800 -- up to 26% more picture          |
| No audio CFs               | Not needed for TV speakers / soundbar setups         |

---

## How It Works

### Architecture

- **Python + `requests`** handles all API interactions
- **YAML config** in the repo holds non-sensitive settings
- **GitHub Secrets** hold credentials and identity
- **Standard GitHub-hosted runners** connect to Ultra.cc services over HTTPS (all services are internet-accessible at `https://{username}.{servername}.usbx.me/{app}`)

### Execution Pipeline

The orchestrator (`scripts/setup.py`) runs services in dependency order:

1. **Validate** -- hit each service's health endpoint; skip unreachable services
2. **qBittorrent** -- set preferences (auto TMM, save path), create categories
3. **Sonarr** -- root folder, qBit download client (tvCategory), media management, tags
4. **Sonarr2** -- same as Sonarr, different instance config
5. **Radarr** -- root folder, qBit download client (movieCategory), media management, tags
6. **Radarr2** -- same as Radarr, different instance config
7. **Prowlarr** -- connect all 4 Arr instances, trigger indexer sync
8. **Jellyfin** -- create 4 media libraries
9. **Jellyseerr** -- add 2 Sonarr + 2 Radarr servers, set default/4K flags

Each service runs in a try/except. Failures are collected, not thrown -- the pipeline continues and the summary reports what failed. Exit code is 0 if everything succeeded, 1 if anything failed.

Ordering matters: Prowlarr runs after the Arr instances (needs their configs to exist), and Jellyseerr runs after Jellyfin.

### API Clients

| Client             | Auth Method                          | Used By                    |
| ------------------ | ------------------------------------ | -------------------------- |
| `ArrClient`        | `X-Api-Key` header                   | Sonarr, Radarr, Prowlarr   |
| `QbitClient`       | Session cookie via form login        | qBittorrent                |
| `JellyfinClient`   | `MediaBrowser Token="{key}"` header  | Jellyfin                   |
| `JellyseerrClient` | `X-Api-Key` header                   | Jellyseerr                 |

All clients share retry with exponential backoff on 5xx and connection errors (3 attempts), and dry-run support that allows GETs but logs and skips all mutations.

---

## Repository Layout

```
.github/
  workflows/
    setup.yml               # Main infrastructure setup workflow
    recyclarr-sync.yml      # Quality profile sync workflow

config/
  config.yml                # Non-sensitive settings (paths, categories, toggles)
  recyclarr.yml             # Recyclarr quality profile definitions

scripts/
  requirements.txt          # Python dependencies (requests, pyyaml)
  setup.py                  # Main orchestrator / entry point
  validate.py               # Connectivity validation

  lib/
    __init__.py
    api_client.py            # HTTP clients (auth, retries, dry-run)
    config_loader.py         # YAML config + secrets merging + path resolution
    logger.py                # Structured summary output

  services/
    __init__.py
    qbittorrent.py           # Preferences, categories
    sonarr.py                # Root folders, download client, media mgmt, tags
    radarr.py                # Root folders, download client, media mgmt, tags
    prowlarr.py              # App connections to all Arr instances
    jellyfin.py              # Library creation
    jellyseerr.py            # Sonarr/Radarr server connections
```

---

## Design Decisions

**Hardlinks enabled** -- Downloads and media folders are on the same filesystem (`/home/{user}/`). Sonarr/Radarr create hardlinks instead of copying, so files don't consume double disk space while seeding.

**Video analysis disabled** -- `enableMediaInfo` is set to `false`. On Ultra.cc shared hosting, media analysis causes unnecessary disk I/O strain with no practical benefit.

**Propers/repacks set to "Do Not Prefer"** -- Repack/proper scoring is handled through Recyclarr custom formats instead, which gives finer control.

**No incomplete/completed download split** -- Torrents download in-place in category subdirectories and seed from the same location. This is the recommended setup per TRaSH Guides.

**Recyclarr is a separate workflow** -- Quality profiles change less frequently than infrastructure. Running Recyclarr independently avoids unnecessary syncs and makes it easy to iterate on profiles without re-running the full setup.

**Jellyseerr runs last** -- It references quality profile names that Recyclarr creates. On first setup this requires a specific three-step order (Setup, Recyclarr, Setup with `services=jellyseerr`). On subsequent runs, the profiles already exist and order doesn't matter.
