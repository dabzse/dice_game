"""
settings.py — Persistent game settings stored in a JSON file.
Remembers player count, player names, and number of rounds between sessions.
"""

import json
import os

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

DEFAULT_SETTINGS = {
    "num_players": 8,
    "num_rounds": 6,
    "player_names": [f"Player {i+1}" for i in range(8)],
}


def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge with defaults to handle missing keys from older saves
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data)
            # Always keep at least 8 name slots so custom names beyond num_players are preserved
            names = merged.get("player_names", [])
            if len(names) < 8:
                names += [f"Player {i+1}" for i in range(len(names), 8)]
            merged["player_names"] = names[:8]
            # Clamp num_players within valid range
            merged["num_players"] = max(2, min(8, merged.get("num_players", DEFAULT_SETTINGS["num_players"])))
            return merged
        except (json.JSONDecodeError, KeyError):
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
