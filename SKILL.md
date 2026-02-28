---
name: playlister
description: "Builds and manages a daily Spotify podcast playlist curated from user-defined topic keywords. Use this skill when the user wants to: build a podcast playlist, refresh their daily podcasts, add or remove podcast topics, set up Spotify for podcast discovery, list their current podcast topics, check playlist status, or find podcast episodes on a specific subject. Trigger phrases include: 'build me a podcast playlist', 'refresh my podcasts', 'add X to my podcast topics', 'remove X from my podcast topics', 'what podcast topics do I have', 'set up my podcast playlist', 'show my playlist status'."
---

# playlister

Curates a daily Spotify playlist of podcast episodes from user-defined topic keywords.
Scripts live at: `~/.openclaw/workspace/skills/playlister/scripts/podcast_playlist.py`

Run all commands as:
```
python3 ~/.openclaw/workspace/skills/playlister/scripts/podcast_playlist.py <command>
```

---

## Actions

### Setup Spotify (first time or re-auth)
**Trigger:** User wants to connect Spotify, configure credentials, or re-authenticate.
```
python3 ~/.openclaw/workspace/skills/playlister/scripts/podcast_playlist.py setup
```
Walk the user through the prompts:
1. Enter Client ID and Client Secret from https://developer.spotify.com/dashboard (press Enter to reuse saved values)
2. Open the printed URL in a browser and authorize the app
3. Copy the full redirect URL from the browser address bar and paste it back
4. Confirm the "Granted scopes" line includes `playlist-modify-public` and `playlist-modify-private`

**If 403 error on playlist creation:** The user's Spotify account is not on the app's allowlist.
Fix: developer.spotify.com/dashboard → select app → Settings → Users Management → Add new user (their email).

### Add a topic
**Trigger:** User wants to add a keyword/subject to their podcast feed.
```
python3 ~/.openclaw/workspace/skills/playlister/scripts/podcast_playlist.py add-topic "TOPIC"
```
Use the user's exact words as the topic keyword. Confirm it was added.

### Remove a topic
**Trigger:** User wants to remove a keyword from their podcast feed.
```
python3 ~/.openclaw/workspace/skills/playlister/scripts/podcast_playlist.py remove-topic "TOPIC"
```
If unsure of the exact name, run `list-topics` first to show current topics.

### List topics
**Trigger:** User wants to see their current podcast topics or settings.
```
python3 ~/.openclaw/workspace/skills/playlister/scripts/podcast_playlist.py list-topics
```

### Build / refresh the playlist
**Trigger:** User wants to build today's playlist, refresh it, or get new episodes.
```
python3 ~/.openclaw/workspace/skills/playlister/scripts/podcast_playlist.py refresh
```
To override the number of episodes per topic (default: 3):
```
python3 ~/.openclaw/workspace/skills/playlister/scripts/podcast_playlist.py refresh --max-episodes N
```
New episodes are prepended to the top of the existing playlist. Already-present episodes are not duplicated.
Report the Spotify playlist URL printed at the end.

### Check status
**Trigger:** User asks if Spotify is connected, wants to see their config, or asks about the skill.
```
python3 ~/.openclaw/workspace/skills/playlister/scripts/podcast_playlist.py status
```

---

## Configuration
Stored at `~/.openclaw/podcast-playlist/config.json`. Key settings:

| Field | Default | Description |
|---|---|---|
| `topics` | `[]` | Podcast topic keywords |
| `episodes_per_topic` | `3` | Episodes fetched per topic per refresh |
| `playlist_visibility` | `"public"` | `"public"` or `"private"` |

## Common errors

| Error | Fix |
|---|---|
| `Not configured` | Run `setup` |
| `401 Unauthorized` | Run `setup` to get a fresh token |
| `403 Forbidden on POST /me/playlists` | Add user's email to app allowlist in Spotify Developer Dashboard → Users Management |
| `No episodes found` | Try broader topic keywords |
| `Invalid redirect URI` | Add `https://pulse.ae:8888/callback` to Spotify app Redirect URIs |

