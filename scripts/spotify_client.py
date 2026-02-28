#!/usr/bin/env python3
"""Spotify API helpers for the podcast-playlist skill.

Provides OAuth setup, token management, episode search, and playlist operations.
All functions raise urllib.error.HTTPError on Spotify API errors.
"""

import base64
import json
import urllib.error
import urllib.parse
import urllib.request

REDIRECT_URI = "https://pulse.ae:8888/callback"
SCOPES = "playlist-modify-public playlist-modify-private playlist-read-private"
_ACCOUNTS = "https://accounts.spotify.com"
_API = "https://api.spotify.com/v1"


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_auth_url(client_id: str) -> str:
    """Return the Spotify authorization URL for the user to open in a browser."""
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
    }
    return f"{_ACCOUNTS}/authorize?" + urllib.parse.urlencode(params)


def _token_request(client_id: str, client_secret: str, data: dict) -> dict:
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        f"{_ACCOUNTS}/api/token",
        data=body,
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    """Exchange a one-time authorization code for access + refresh tokens."""
    return _token_request(client_id, client_secret, {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    })


def get_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    """Get a fresh access token using the stored refresh token."""
    return _token_request(client_id, client_secret, {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    })["access_token"]


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _spotify_error(e: urllib.error.HTTPError, method: str, path: str) -> RuntimeError:
    """Wrap an HTTPError with the Spotify error body for a readable message."""
    try:
        detail = json.loads(e.read()).get("error", {}).get("message", "")
    except Exception:
        detail = ""
    return RuntimeError(
        f"Spotify {e.code} on {method} {path}"
        + (f": {detail}" if detail else "")
    )


def _get(token: str, path: str, params: dict | None = None) -> dict:
    url = f"{_API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise _spotify_error(e, "GET", path) from e


def _post(token: str, path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{_API}{path}",
        data=json.dumps(body).encode(),
        headers=_headers(token),
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise _spotify_error(e, "POST", path) from e


def _put(token: str, path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{_API}{path}",
        data=json.dumps(body).encode(),
        method="PUT",
        headers=_headers(token),
    )
    try:
        with urllib.request.urlopen(req) as r:
            content = r.read()
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        raise _spotify_error(e, "PUT", path) from e


# ── Spotify API operations ────────────────────────────────────────────────────

def get_current_user(token: str) -> dict:
    """Return the current user's Spotify profile."""
    return _get(token, "/me")


def search_episodes(token: str, query: str, limit: int = 10) -> list[dict]:
    """Search for podcast episodes matching query. Returns a list of episode objects."""
    result = _get(token, "/search", {
        "q": query,
        "type": "episode",
        "market": "US",
        "limit": min(limit, 50),
    })
    return [ep for ep in result.get("episodes", {}).get("items", []) if ep]


def get_user_playlists(token: str) -> list[dict]:
    """Fetch all of the current user's playlists (handles pagination automatically)."""
    playlists: list[dict] = []
    path = "/me/playlists"
    params: dict | None = {"limit": 50}
    while path:
        result = _get(token, path, params)
        playlists.extend(p for p in result.get("items", []) if p)
        nxt = result.get("next")
        path = nxt.replace(_API, "") if nxt else None
        params = None
    return playlists


def create_playlist(
    token: str, name: str, description: str, public: bool = True
) -> dict:
    """Create a new playlist for the current user and return the playlist object."""
    return _post(token, "/me/playlists", {
        "name": name,
        "description": description,
        "public": public,
    })


def set_playlist_items(token: str, playlist_id: str, uris: list[str]) -> None:
    """Replace all items in a playlist with the given episode URIs."""
    # PUT with first batch replaces the playlist; POST appends the rest.
    if not uris:
        _put(token, f"/playlists/{playlist_id}/items", {"uris": []})
        return
    _put(token, f"/playlists/{playlist_id}/items", {"uris": uris[:100]})
    for i in range(100, len(uris), 100):
        _post(token, f"/playlists/{playlist_id}/items", {"uris": uris[i:i + 100]})


def get_playlist_item_uris(token: str, playlist_id: str) -> list[str]:
    """Return all track/episode URIs currently in a playlist, in order."""
    uris: list[str] = []
    path = f"/playlists/{playlist_id}/items"
    params: dict | None = {"limit": 50, "fields": "next,items(track(uri))"}
    while path:
        result = _get(token, path, params)
        for item in result.get("items", []):
            uri = (item.get("track") or {}).get("uri")
            if uri:
                uris.append(uri)
        nxt = result.get("next")
        path = nxt.replace(_API, "") if nxt else None
        params = None
    return uris


def prepend_items(token: str, playlist_id: str, uris: list[str]) -> None:
    """Insert URIs at the beginning of a playlist, preserving their order."""
    # Insert in chunks of 100, advancing the offset so order is maintained.
    for i in range(0, len(uris), 100):
        _post(token, f"/playlists/{playlist_id}/items", {
            "uris": uris[i:i + 100],
            "position": i,
        })


def update_playlist_details(
    token: str, playlist_id: str, name: str | None = None, description: str | None = None
) -> None:
    """Update the name and/or description of an existing playlist."""
    body = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if body:
        _put(token, f"/playlists/{playlist_id}", body)

