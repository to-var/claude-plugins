"""Reading the user's Claude settings.json without ever clobbering it."""
from . import TovarError, files, paths


def as_dict(value):
    return value if isinstance(value, dict) else {}


def load():
    """The settings as a dict. A missing or empty file is {}. An unreadable one stops the command."""
    text = files.read_text(paths.settings_path())
    if text is None or not text.strip():
        return {}
    settings = files.read_json_file(paths.settings_path())
    if not isinstance(settings, dict):
        raise TovarError(f"{paths.settings_path()} is not a JSON object, so nothing was changed.")
    return settings
