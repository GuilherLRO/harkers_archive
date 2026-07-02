# Remote machine + data sync

Run **Helsing's Round** on a second computer (NAS, VPS, home server) while keeping `voice_archive/`, `transcripts/`, `dossier/`, `logs/`, and weekly Rainfields notes in sync with your **main Mac**.

Two compose files work together:

| File | Machine | What runs |
|------|---------|-----------|
| [`docker-compose.sync.yml`](../docker-compose.sync.yml) | **Main** (Mac) | Syncthing only — shares archive folders |
| [`docker-compose.remote.yml`](../docker-compose.remote.yml) | **Remote** | Syncthing + `helsings_round.py` |

Same-machine Docker (no cross-machine sync): [`docker-compose.yml`](../docker-compose.yml).

---

## Architecture

```text
Main Mac                              Remote machine
┌─────────────────────┐              ┌──────────────────────────┐
│ voice_archive/      │◄──Syncthing──►│ voice_archive/           │
│ transcripts/        │              │ transcripts/             │
│ dossier/            │              │ dossier/                 │
│ logs/               │              │ logs/                    │
│ rainfields_mind/    │              │ rainfields_mind/weekly/  │
│   weekly/           │              │                          │
├─────────────────────┤              ├──────────────────────────┤
│ docker-compose.sync │              │ docker-compose.remote    │
│   → syncthing       │              │   → syncthing            │
│                     │              │   → helsings-round       │
│ helsings_roundctl   │  (optional)  │   (runs the Telegram bot)│
│ OR stopped if remote│              │                          │
└─────────────────────┘              └──────────────────────────┘
```

Syncthing keeps folders **bidirectional** — new voice files from Telegram on the remote appear on your Mac; typed notes captured on main sync to remote.

---

## Prerequisites

- **Git** on both machines (clone this repo).
- **Docker + Compose** on the remote; Docker on main if you use the sync container (or [Syncthing for Mac](https://syncthing.net/downloads/) instead).
- **Same secrets on remote** — copy `.env` from main through a **secure channel** (AirDrop, password manager, `scp`). **Do not** put `.env` in Syncthing.
- **Network** — both machines reach each other on port `22000` (sync). Easiest: [Tailscale](https://tailscale.com/) on both; then use Tailscale IPs in Syncthing.
- **One bot instance** — only one `helsings_round` / Telegram poller. If the remote runs the bot, run `./helsings_roundctl.sh stop` on main.

---

## Step 1 — Main machine (sync partner)

From the repo root, with archive folders already in use:

```bash
docker compose -f docker-compose.sync.yml up -d
```

Open **http://127.0.0.1:8384**, set a GUI password (Actions → Settings).

**Alternative:** install Syncthing.app on macOS and add the same folder paths (`voice_archive`, `transcripts`, `dossier`, `logs`, `rainfields_mind/weekly`) instead of the sync compose file.

---

## Step 2 — Remote machine (runner)

```bash
git clone https://github.com/GuilherLRO/harkers_archive.git
cd harkers_archive
cp .env.example .env
# Edit .env — at minimum TELEGRAM_BOT_TOKEN; OPENAI_API_KEY if Rainfields is enabled
mkdir -p voice_archive transcripts dossier logs rainfields_mind/weekly

docker compose -f docker-compose.remote.yml up -d --build
```

Open **http://&lt;remote-ip&gt;:8384** (or Tailscale IP).

---

## Step 3 — Pair Syncthing (once)

On **each** Syncthing UI:

1. **Add remote device** — paste the other machine's Device ID (shown under Actions → Show ID).
2. **Add folder** for each path below. Use the **same Folder ID** on both sides (e.g. `harkers-voice`).

| Folder ID (example) | Path on main | Path on remote (in container → host) |
|-------------------|--------------|--------------------------------------|
| `harkers-voice` | `…/voice_archive` | `…/voice_archive` |
| `harkers-transcripts` | `…/transcripts` | `…/transcripts` |
| `harkers-dossier` | `…/dossier` | `…/dossier` |
| `harkers-logs` | `…/logs` | `…/logs` |
| `harkers-rainfields-weekly` | `…/rainfields_mind/weekly` | `…/rainfields_mind/weekly` |

In the Syncthing UI, folder path on the **remote Docker** side is `/data/voice_archive`, etc. (mapped to host `./voice_archive`).

3. Share each folder with the paired device. Accept incoming shares on the other side.
4. Wait until status is **Up to Date** before relying on synced files.

**Tips**

- Set folder type to **Send & Receive** on both (default bidirectional sync).
- For large initial sync, leave both machines on until complete.
- `rainfields_mind/` code (README, agent) comes from **git pull**, not Syncthing — only `weekly/` is synced.

---

## Step 4 — Choose where the bot runs

| Setup | Main Mac | Remote |
|-------|----------|--------|
| **Remote runs 24/7** | `./helsings_roundctl.sh stop` | `docker compose -f docker-compose.remote.yml up -d` |
| **Main runs bot, remote is backup/sync only** | `./helsings_roundctl.sh start` | Do **not** start `helsings-round` — use a custom override or only `docker-compose.sync.yml` on remote |

Default remote compose **starts the bot**. Stop it on main first.

---

## Day-to-day commands

**Remote**

```bash
docker compose -f docker-compose.remote.yml logs -f helsings-round
docker compose -f docker-compose.remote.yml restart
docker compose -f docker-compose.remote.yml down        # stops bot + syncthing
```

**Main (sync only)**

```bash
docker compose -f docker-compose.sync.yml logs -f
docker compose -f docker-compose.sync.yml down
```

**Update code on remote**

```bash
git pull
docker compose -f docker-compose.remote.yml up -d --build
```

Rebuild when `uv.lock` or the Dockerfile changes.

---

## Security

| Do | Don't |
|----|--------|
| Keep `.env` gitignored; copy secrets manually | Sync `.env` via Syncthing |
| Use Tailscale or private LAN for Syncthing | Expose port 8384 to the public internet without a GUI password |
| One Telegram bot poller | Run bot on main and remote simultaneously |
| Bind-mount data dirs only | Bake secrets into the Docker image |

Python dependencies are **inside the image** (`docker compose build`). Data files sync via **Syncthing**, not via git.

---

## Troubleshooting

| Issue | Check |
|-------|--------|
| Remote bot not receiving messages | Only one instance running? Token correct in remote `.env`? |
| Files missing on main | Syncthing folder **Up to Date**? Correct paths on both sides? |
| Conflict copies (`*.sync-conflict-*`) | Normal under simultaneous edits; resolve manually in Syncthing UI |
| Whisper slow on remote | First run downloads models into `whisper-cache` volume; ensure enough RAM |
| Port 8384 in use on main | Change `SYNCTHING_GUI_PORT` in `.env` or stop other Syncthing instances |

Optional env vars (both compose files):

```bash
SYNCTHING_HOSTNAME=harkers-main    # or harkers-remote
SYNCTHING_GUI_PORT=8384
SYNCTHING_SYNC_PORT=22000
```
