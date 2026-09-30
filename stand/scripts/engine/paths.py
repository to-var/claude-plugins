"""Where Stand reads and writes."""
import os
from pathlib import Path

from . import StandError

PLUGIN = Path(__file__).resolve().parents[2]


def config_dir():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def data_dir():
    raw = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not raw:
        raise StandError("CLAUDE_PLUGIN_DATA is not set. Run the command with --data <folder>.")
    return Path(raw)


def examples_dir():
    return Path(os.environ.get("STAND_EXAMPLES") or PLUGIN / "examples")


def settings_path():
    return config_dir() / "settings.json"


def claude_md_path():
    return config_dir() / "CLAUDE.md"


def styles_dir():
    return config_dir() / "output-styles"
