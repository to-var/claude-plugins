"""state.json: what Stand last applied. The real files are the truth, see each area's active check."""
from . import files, paths

DEFAULT = {"theme": None, "style": None, "style_setting": None, "memory": []}


def path():
    return paths.data_dir() / "state.json"


def load():
    data = files.read_json_file(path())
    data = data if isinstance(data, dict) else {}
    loaded = {**DEFAULT, **data}
    loaded["memory"] = list(loaded["memory"]) if isinstance(loaded["memory"], list) else []
    return loaded


def save(state):
    files.atomic_write(path(), files.dump_json(state))
