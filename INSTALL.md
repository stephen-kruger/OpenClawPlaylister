---
name: podcast-playlist
description: >
  Assembles a daily Spotify playlist of podcast episodes curated by topic keywords.
  Use this skill when the user wants to: discover new podcast episodes on specific
  topics, create or refresh a daily podcast playlist on Spotify, manage their podcast
  topic preferences, configure Spotify integration for podcast discovery, or
  automatically pull episodes from multiple shows into one playlist by subject area.
  Trigger phrases include: "build me a podcast playlist", "add AI to my podcast topics",
  "refresh my daily podcasts", "set up podcast playlist", "what podcasts are there about X".
---

# Podcast Playlist

## Installing into OpenClaw

Skills live in `~/.openclaw/workspace/skills/` (workspace-scoped, highest priority) or
`~/.openclaw/skills/` (shared across all agents). Either location works; the workspace
path is recommended so the skill is kept with your personal configuration.

### Option A — Clone directly into the skills directory (recommended)

```bash
git clone https://github.com/stephen-kruger/OpenClawPlaylister.git \
  ~/.openclaw/workspace/skills/playlister
```

### Option B — Copy from a local checkout

```bash
cp -r /path/to/OpenClawPlaylister ~/.openclaw/workspace/skills/playlister
```

### Verify the skill is recognised

```bash
openclaw skills list
```

`playlister` should appear in the output. If it shows but is not marked **eligible**,
confirm Python 3.8+ is on the PATH that the OpenClaw gateway uses:

```bash
openclaw doctor --repair
```

### Restart the gateway

OpenClaw snapshots skills at startup, so a restart is required after installing:

```bash
openclaw gateway restart
```

After the restart, simply ask your agent naturally — for example:
- *"Set up my podcast playlist"*
- *"Add machine learning to my podcast topics"*
- *"Refresh my daily podcasts"*

OpenClaw will match the request to this skill automatically via the description in
`SKILL.md` and execute the appropriate command.

---

## About

Builds a fresh Spotify playlist of podcast episodes each day, curated by
user-defined topic keywords. Each topic is searched independently so episodes
from multiple subjects end up in one convenient playlist.

## Requirements

- Python 3.8+
- A Spotify account
- A Spotify Developer App (free) at https://developer.spotify.com/dashboard

Scripts live in `scripts/` next to this file:
- `spotify_client.py` — Spotify API helpers (imported automatically)
- `podcast_playlist.py` — Main CLI (all commands below use this)

Run commands from the `scripts/` directory:
```bash
cd scripts/
python podcast_playlist.py <command>
```

## One-Time Setup

1. Go to https://developer.spotify.com/dashboard → **Create app**
2. Set the Redirect URI to `https://pulse.ae:8888/callback` and save
3. Copy the **Client ID** and **Client Secret**
4. Run setup:
   ```bash
   python podcast_playlist.py setup
   ```
5. Follow the prompts: paste credentials → open the printed URL in a browser →
   authorize → copy the full redirect URL from the browser address bar (even if
   the page shows an error) → paste it back into the terminal

## Managing Topics

```bash
python podcast_playlist.py add-topic "machine learning"
python podcast_playlist.py add-topic "climate change"
python podcast_playlist.py add-topic "personal finance"
python podcast_playlist.py remove-topic "personal finance"
python podcast_playlist.py list-topics
```

## Building the Daily Playlist

```bash
# Build today's playlist using all configured topics
python podcast_playlist.py refresh

# Override how many episodes per topic (default: 3)
python podcast_playlist.py refresh --max-episodes 5
```

Creates a Spotify playlist named `Daily Podcasts – YYYY-MM-DD`. If a playlist for
today already exists it is updated in place. The Spotify URL is printed when done.

## Check Status

```bash
python podcast_playlist.py status
```

## Configuration

Stored at `~/.openclaw/podcast-playlist/config.json`. Key fields:

| Field | Default | Description |
|---|---|---|
| `topics` | `[]` | Podcast topic keywords |
| `episodes_per_topic` | `3` | Episodes fetched per topic |
| `playlist_visibility` | `"public"` | `"public"` or `"private"` |

Edit the file directly to change defaults, or ask the user which values to set.

## Daily Automation (Optional)

Add to `HEARTBEAT.md` or a cron job to refresh automatically each morning:
```
# cron: refresh playlist at 07:00 daily
0 7 * * * cd /path/to/skills/podcast-playlist/scripts && python podcast_playlist.py refresh
```

## Troubleshooting

| Error | Fix |
|---|---|
| `Not configured` | Run `setup` first |
| `No episodes found` | Use broader topic keywords |
| `401 Unauthorized` | Re-run `setup` to refresh credentials |
| `Invalid redirect URI` | Add `https://pulse.ae:8888/callback` to Spotify app settings |

