#!/usr/bin/env python3
"""podcast-playlist: Daily Spotify podcast playlist builder.

Usage:
    python podcast_playlist.py setup
    python podcast_playlist.py add-topic "machine learning"
    python podcast_playlist.py remove-topic "machine learning"
    python podcast_playlist.py list-topics
    python podcast_playlist.py refresh [--max-episodes N]
    python podcast_playlist.py status
"""

import argparse
import json
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

# Allow running from any directory by resolving the sibling module.
sys.path.insert(0, str(Path(__file__).parent))
import spotify_client as sc

CONFIG_DIR = Path.home() / ".openclaw" / "podcast-playlist"
CONFIG_FILE = CONFIG_DIR / "config.json"
_DEFAULTS: dict = {
    "topics": [],
    "episodes_per_topic": 3,
    "playlist_visibility": "public",
    "search_strategy": "individual",   # "individual" | "combined"
    "sort_by": "recency",              # "recency" | "relevance"
    "spotify": {"client_id": "", "client_secret": "", "refresh_token": "", "user_id": ""},
}


# ── Config helpers ─────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        cfg = json.loads(CONFIG_FILE.read_text())
        for k, v in _DEFAULTS.items():
            cfg.setdefault(k, v)
        return cfg
    return {k: (v.copy() if isinstance(v, dict) else list(v) if isinstance(v, list) else v)
            for k, v in _DEFAULTS.items()}


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def _token(cfg: dict) -> str:
    sp = cfg["spotify"]
    if not sp.get("client_id") or not sp.get("refresh_token"):
        sys.exit("Error: Spotify not configured. Run 'setup' first.")
    return sc.get_access_token(sp["client_id"], sp["client_secret"], sp["refresh_token"])


# ── Commands ───────────────────────────────────────────────────────────────────

def cmd_setup(args: argparse.Namespace) -> None:
    cfg = load_config()
    sp = cfg["spotify"]
    print("=== Podcast Playlist – Spotify Setup ===\n")

    saved_id = sp.get("client_id", "")
    saved_secret = sp.get("client_secret", "")

    if saved_id:
        print(f"Spotify Client ID [{saved_id}]: ", end="", flush=True)
        client_id = input().strip() or saved_id
    else:
        client_id = input("Spotify Client ID: ").strip()

    if saved_secret:
        masked = saved_secret[:4] + "*" * (len(saved_secret) - 4)
        print(f"Spotify Client Secret [{masked}]: ", end="", flush=True)
        client_secret = input().strip() or saved_secret
    else:
        client_secret = input("Spotify Client Secret: ").strip()

    if not client_id or not client_secret:
        sys.exit("Error: Both Client ID and Client Secret are required.")

    auth_url = sc.get_auth_url(client_id)
    print(f"\n1. Open this URL in your browser:\n   {auth_url}")
    print("2. Authorize the app. You'll be redirected to https://pulse.ae:8888/callback.")
    print("   The page will show a connection error — that's expected.")
    print("   Copy the full URL from the browser address bar.\n")
    redirect = input("3. Paste the full redirect URL here: ").strip()

    qs = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    code = qs.get("code", [None])[0]
    if not code:
        sys.exit("Error: Could not find authorization code in the URL.")

    tokens = sc.exchange_code(client_id, client_secret, code)
    granted_scopes = tokens.get("scope", "")
    user = sc.get_current_user(tokens["access_token"])
    cfg["spotify"] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": tokens["refresh_token"],
        "user_id": user["id"],
    }
    save_config(cfg)
    print(f"\n✓ Authenticated as: {user.get('display_name', user['id'])} ({user['id']})")
    print(f"  Granted scopes : {granted_scopes}")

    required = {"playlist-modify-public", "playlist-modify-private"}
    missing = required - set(granted_scopes.split())
    if missing:
        print(f"\n⚠ WARNING: Missing required scopes: {', '.join(missing)}")
        print("  Playlist creation will fail. Check your Spotify app's settings")
        print("  in the Developer Dashboard and ensure it has access to these scopes.")
    else:
        print("  ✓ All required scopes granted.")
    print(f"  Config saved to: {CONFIG_FILE}")


def cmd_add_topic(args: argparse.Namespace) -> None:
    cfg = load_config()
    topic = args.topic.strip().lower()
    if topic in cfg["topics"]:
        print(f"Topic '{topic}' is already in the list.")
    else:
        cfg["topics"].append(topic)
        save_config(cfg)
        print(f"✓ Added '{topic}'.  Topics: {', '.join(cfg['topics'])}")


def cmd_remove_topic(args: argparse.Namespace) -> None:
    cfg = load_config()
    topic = args.topic.strip().lower()
    if topic not in cfg["topics"]:
        print(f"Topic '{topic}' not found.")
    else:
        cfg["topics"].remove(topic)
        save_config(cfg)
        remaining = ", ".join(cfg["topics"]) or "(none)"
        print(f"✓ Removed '{topic}'.  Remaining: {remaining}")


def cmd_list_topics(args: argparse.Namespace) -> None:
    cfg = load_config()
    topics = cfg["topics"]
    print(f"Topics ({len(topics)}): {', '.join(topics) or '(none)'}")
    print(f"Episodes per topic : {cfg['episodes_per_topic']}")
    print(f"Playlist visibility: {cfg['playlist_visibility']}")
    print(f"Search strategy    : {cfg['search_strategy']}")
    print(f"Sort by            : {cfg['sort_by']}")


def cmd_refresh(args: argparse.Namespace) -> None:
    cfg = load_config()
    if not cfg["topics"]:
        sys.exit("Error: No topics configured. Use 'add-topic' first.")

    per_topic = args.max_episodes or cfg["episodes_per_topic"]
    strategy = args.strategy or cfg["search_strategy"]
    sort_by = args.sort or cfg["sort_by"]
    token = _token(cfg)
    today = datetime.now().strftime("%Y-%m-%d")
    playlist_name = "Daily Playlister"

    print(f"Refreshing '{playlist_name}' [strategy={strategy}, sort={sort_by}]...")
    all_eps: list[dict] = []
    seen: set[str] = set()

    if strategy == "combined":
        # Single API call — all topics ORed together in one query.
        total_limit = min(per_topic * len(cfg["topics"]), 50)
        topic_list = ", ".join(cfg["topics"])
        print(f"  Searching (combined): {topic_list}...", end=" ", flush=True)
        episodes = sc.search_episodes_combined(token, cfg["topics"],
                                               limit=total_limit,
                                               sort_by=sort_by)
        for ep in episodes:
            uri = ep.get("uri")
            if uri and uri not in seen:
                seen.add(uri)
                all_eps.append({"topic": "combined", "ep": ep})
        print(f"{len(all_eps)} episode(s) found")
    else:
        # Individual strategy — one search per topic, capped at per_topic each.
        for topic in cfg["topics"]:
            print(f"  Searching: {topic}...", end=" ", flush=True)
            episodes = sc.search_episodes(
                token, f"podcast {topic}", limit=per_topic * 2, sort_by=sort_by
            )
            added = 0
            for ep in episodes:
                uri = ep.get("uri")
                if uri and uri not in seen:
                    seen.add(uri)
                    all_eps.append({"topic": topic, "ep": ep})
                    added += 1
                    if added >= per_topic:
                        break
            print(f"{added} episode(s) found")

    if not all_eps:
        sys.exit("No episodes found. Try different topics or re-run 'setup'.")

    uris = [x["ep"]["uri"] for x in all_eps]
    desc = f"Topics: {', '.join(cfg['topics'])}. Last updated {today} by playlister."

    try:
        playlists = sc.get_user_playlists(token)
        existing = next((p for p in playlists if p and p.get("name") == playlist_name), None)

        if existing:
            print("  Fetching existing playlist items...")
            existing_uris = sc.get_playlist_item_uris(token, existing["id"])
            existing_set = set(existing_uris)
            new_uris = [u for u in uris if u not in existing_set]
            if new_uris:
                print(f"  Prepending {len(new_uris)} new episode(s)...")
                sc.prepend_items(token, existing["id"], new_uris)
            else:
                print("  No new episodes to add (all already in playlist).")
            sc.update_playlist_details(token, existing["id"], description=desc)
            url = existing["external_urls"]["spotify"]
        else:
            print("  Creating new playlist...")
            public = cfg["playlist_visibility"] == "public"
            playlist = sc.create_playlist(token, playlist_name, desc, public)
            sc.set_playlist_items(token, playlist["id"], uris)
            url = playlist["external_urls"]["spotify"]
    except RuntimeError as e:
        msg = str(e)
        if "403" in msg:
            sys.exit(
                f"Error: {msg}\n\n"
                "403 Forbidden means your Spotify account is not on the app's allowlist.\n"
                "Fix (takes 1 minute):\n"
                "  1. Go to developer.spotify.com/dashboard\n"
                "  2. Select your app → Settings → Users Management tab\n"
                "  3. Click 'Add new user' and enter your Spotify account's name and email\n"
                "  4. Then retry 'refresh'\n\n"
                "Note: Development mode apps require every user (including yourself as the owner)\n"
                "to be explicitly added to the allowlist before API write calls will succeed."
            )
        raise

    print(f"\n\u2713 {len(all_eps)} episode(s) prepended to '{playlist_name}':")
    for x in all_eps:
        ep = x["ep"]
        show = ep.get("show", {}).get("name", "Unknown Show")
        title = ep.get("name", "Unknown Episode")[:55]
        print(f"  [{x['topic']}] {show} \u2014 {title}")
    print(f"\n\U0001f3a7 {url}")


def cmd_status(args: argparse.Namespace) -> None:
    cfg = load_config()
    sp = cfg["spotify"]
    ok = bool(sp.get("client_id") and sp.get("refresh_token"))
    conn = f"\u2713 Connected (user: {sp.get('user_id', '?')})" if ok else "\u2717 Not configured (run 'setup')"
    print(f"Spotify          : {conn}")
    print(f"Topics           : {', '.join(cfg['topics']) or '(none)'}")
    print(f"Episodes/topic   : {cfg['episodes_per_topic']}")
    print(f"Visibility       : {cfg['playlist_visibility']}")
    print(f"Config file      : {CONFIG_FILE}")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a daily Spotify podcast playlist from topic keywords"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help="Configure Spotify credentials via OAuth")
    p = sub.add_parser("add-topic", help="Add a podcast topic keyword")
    p.add_argument("topic", help='e.g. "machine learning"')
    p = sub.add_parser("remove-topic", help="Remove a topic keyword")
    p.add_argument("topic", help="Topic to remove")
    sub.add_parser("list-topics", help="List current topic keywords and settings")
    p = sub.add_parser("refresh", help="Build or refresh today\u2019s playlist")
    p.add_argument("--max-episodes", type=int, metavar="N",
                   help="Override episodes per topic (default from config)")
    p.add_argument("--strategy", choices=["individual", "combined"],
                   help="individual: one search per topic; combined: all topics in one OR query")
    p.add_argument("--sort", choices=["recency", "relevance"],
                   help="recency: newest episodes first; relevance: Spotify ranking (default)")
    sub.add_parser("status", help="Show configuration and connection status")

    args = parser.parse_args()
    {
        "setup": cmd_setup,
        "add-topic": cmd_add_topic,
        "remove-topic": cmd_remove_topic,
        "list-topics": cmd_list_topics,
        "refresh": cmd_refresh,
        "status": cmd_status,
    }[args.command](args)


if __name__ == "__main__":
    main()

