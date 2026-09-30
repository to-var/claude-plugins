"""Reading the user's Claude settings.json without ever clobbering it."""
from . import StandError, files, paths


def as_dict(value):
    return value if isinstance(value, dict) else {}


def load():
    """The settings as a dict. A missing file is {}. An unreadable one stops the command."""
    settings = files.read_json_file(paths.settings_path())
    if settings is None:
        return {}
    if not isinstance(settings, dict):
        raise StandError(f"{paths.settings_path()} is not a JSON object, so nothing was changed.")
    return settings
