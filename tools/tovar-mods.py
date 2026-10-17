#!/usr/bin/env python3
"""Builder for the character bars and plugins in this marketplace.

One plugin, tovar-mods, holds the engine and every bar. A bar is only data:
tovar-mods/bars/<bar>/roster.ts plus characters/*.md.

  new <bar>                          make a bar from tovar-bar-template, then list it in
                                     hooks/bars.ts and in the Bar setting
  register <plugin> <description>    list a hand-made plugin folder at the repo root in the
                                     marketplace (the name must start with "tovar-")
  check [bar ...]                    check each bar's roster and profiles and that it is
                                     listed, then run the plugin checker and tests once
  overlap <bar> <theme> [--data DIR] check that a tovar theme's spinner verbs never
                                     repeat the bar: no verb equal to a thinking
                                     action, no verb naming a bar character
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "tovar-bar-template"
PLUGIN = ROOT / "tovar-mods"
BARS = PLUGIN / "bars"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
TOVAR = ROOT / "tovar-core" / "scripts" / "tovar.py"
TOVAR_DATA = Path.home() / ".claude" / "plugins" / "data" / "tovar-core-tovar"
PREFIX = "tovar-"
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SKIP = {".DS_Store", "__pycache__"}
TODO = "TODO(tovar-new-bar)"
MOODS = ("calm", "working", "burning")
HEX = re.compile(r"^- \*\*Color:\*\* #[0-9a-fA-F]{6}\b", re.M)
EMOJI = re.compile(r"^- \*\*Emoji:\*\* \S+", re.M)
SPEAKS = re.compile(r"^- \*\*Speaks:\*\* \S+", re.M)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slug(name):
    """The profile file name for a character, as the mod's code builds it."""
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", name.lower()))


def bar_names():
    if not BARS.is_dir():
        return []
    return sorted(p.name for p in BARS.iterdir() if (p / "roster.ts").is_file())


def write_bar_list():
    names = bar_names()
    lines = [
        "// Every bar, by the name the Bar setting uses. Written by tools/tovar-mods.py.",
        "import type { Roster } from './character'",
        *[f"import {{ ROSTER as bar{i} }} from '../bars/{n}/roster'" for i, n in enumerate(names)],
        "",
        "export const BARS: Record<string, Roster> = {",
        *[f"  '{n}': bar{i}," for i, n in enumerate(names)],
        "}",
        "",
    ]
    (PLUGIN / "hooks" / "bars.ts").write_text("\n".join(lines), encoding="utf-8")


def write_bar_setting():
    """Rewrite only the Bar options array, so the rest of plugin.json keeps its style."""
    manifest = PLUGIN / ".claude-plugin" / "plugin.json"
    text = manifest.read_text(encoding="utf-8")
    options = json.dumps(bar_names() + ["off"], ensure_ascii=False)
    new, n = re.subn(r'("bar":\s*\{.*?"options":\s*)\[[^\]]*\]', lambda m: m.group(1) + options, text, count=1, flags=re.S)
    if n != 1:
        sys.exit("Could not find the Bar options in tovar-mods/.claude-plugin/plugin.json.")
    manifest.write_text(new, encoding="utf-8")


def add_to_marketplace(plugin, description):
    market = read_json(MARKETPLACE)
    plugins = market.setdefault("plugins", [])
    if any(p.get("name") == plugin for p in plugins):
        return False
    plugins.append({"name": plugin, "source": f"./{plugin}", "description": description})
    write_json(MARKETPLACE, market)
    return True


def cmd_new(args):
    if len(args) != 1:
        sys.exit("usage: tovar-mods.py new <bar>")
    bar = args[0]
    if bar == "off":
        sys.exit("'off' is the Bar setting's way to switch bars off, so it cannot be a bar name.")
    if not NAME.match(bar):
        sys.exit(f"'{bar}' is not a valid bar name. Use lowercase letters, digits and hyphens.")
    dest = BARS / bar
    if dest.exists():
        sys.exit(f"tovar-mods/bars/{bar} already exists.")
    shutil.copytree(TEMPLATE, dest, ignore=shutil.ignore_patterns(*SKIP))
    write_bar_list()
    write_bar_setting()

    print(f"Created tovar-mods/bars/{bar} and listed it in hooks/bars.ts and the Bar setting.")
    print("Fill in roster.ts and one profile per character in characters/,")
    print(f"remove the examples, then run: python3 tools/tovar-mods.py check {bar}")


def cmd_register(args):
    if len(args) != 2:
        sys.exit('usage: tovar-mods.py register <plugin> "<description>"')
    plugin, description = args
    if not plugin.startswith(PREFIX):
        sys.exit(f"Plugin names must start with '{PREFIX}', got '{plugin}'.")
    if not (ROOT / plugin / ".claude-plugin" / "plugin.json").is_file():
        sys.exit(f"{plugin} has no .claude-plugin/plugin.json.")
    if add_to_marketplace(plugin, description):
        print(f"Listed {plugin} in the marketplace.")
    else:
        print(f"{plugin} is already listed.")


def roster_names(text):
    """The character names per mood in roster.ts, read with a light parser."""
    found = {}
    for mood in MOODS:
        m = re.search(rf"\b{mood}:\s*\[(.*?)\]\s*,?\s*(?:\n|$)", text, re.S)
        if m:
            found[mood] = re.findall(r"""name:\s*(['"])(.*?)\1""", m.group(1))
            found[mood] = [n for _, n in found[mood]]
    return found


QUOTED = r"""(?:'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")"""


def unquote(q):
    return re.sub(r"\\(.)", r"\1", q[1:-1])


def roster_entries(text):
    """Each character in roster.ts as (name, thinking actions or None)."""
    entry = re.compile(
        rf"\{{\s*name:\s*({QUOTED})(?:\s*,\s*thinks:\s*\[((?:\s*{QUOTED}\s*,?)*)\s*\])?\s*\}}"
    )
    found = []
    for m in entry.finditer(text):
        thinks = None if m.group(2) is None else [unquote(t) for t in re.findall(QUOTED, m.group(2))]
        found.append((unquote(m.group(1)), thinks))
    return found


def generic_thinking():
    """The engine's fallback thinking actions, for characters with none of their own."""
    code = (PLUGIN / "hooks" / "narration.ts").read_text(encoding="utf-8")
    m = re.search(r"const THINKING = \[(.*?)\]", code, re.S)
    return [t for _, t in re.findall(r"""(['"])(.*?)\1""", m.group(1))] if m else []


def plain(text):
    return re.sub(r"\s+", " ", re.sub(r"(…|\.\.\.)\s*$", "", text)).strip().lower()


def theme_verbs(theme, data):
    r = subprocess.run(
        [sys.executable, str(TOVAR), "--data", str(data), "theme", "show", theme, "--json"],
        capture_output=True, text=True,
    )
    try:
        return json.loads(r.stdout)["data"]["verbs"]
    except (ValueError, KeyError, TypeError):
        sys.exit(f"Could not read theme '{theme}':\n{(r.stdout + r.stderr).strip()}")


def cmd_overlap(args):
    data = TOVAR_DATA
    if "--data" in args:
        i = args.index("--data")
        if i + 1 >= len(args):
            sys.exit("usage: tovar-mods.py overlap <bar> <theme> [--data DIR]")
        data = Path(args[i + 1])
        args = args[:i] + args[i + 2:]
    if len(args) != 2:
        sys.exit("usage: tovar-mods.py overlap <bar> <theme> [--data DIR]")
    bar, theme = args
    roster = BARS / bar / "roster.ts"
    if not roster.is_file():
        sys.exit(f"tovar-mods/bars/{bar} has no roster.ts, so it is not a bar.")
    entries = roster_entries(roster.read_text(encoding="utf-8"))
    generic = generic_thinking()
    actions = {}
    for name, thinks in entries:
        for action in thinks if thinks is not None else generic:
            actions.setdefault(plain(action), []).append(name)

    found = []
    for verb in theme_verbs(theme, data):
        who = actions.get(plain(verb))
        if who:
            found.append(f'"{verb}" is also a thinking action of {", ".join(sorted(set(who)))}')
        named = [n for n, _ in entries if re.search(rf"(?<!\w){re.escape(n)}(?!\w)", verb, re.I)]
        if named:
            found.append(f'"{verb}" names {", ".join(named)}, who is in the bar')
    if found:
        print(f"{bar} vs theme {theme}:")
        for p in found:
            print(f"  - {p}")
        sys.exit(1)
    print(f"{bar} vs theme {theme}: OK")


def roster_problems(d):
    roster = d / "roster.ts"
    if not roster.is_file():
        return ["no roster.ts"]
    found = []
    text = roster.read_text(encoding="utf-8")
    if TODO in text:
        found.append("roster.ts still has the TODO line or the example characters")
    names = roster_names(text)
    for mood in MOODS:
        if not names.get(mood):
            found.append(f"roster.ts: {mood} has no characters")
    every = [n for mood in MOODS for n in names.get(mood, [])]
    repeated = sorted({n for n in every if every.count(n) > 1})
    if repeated:
        found.append(f"roster.ts: repeated: {', '.join(repeated)}")

    folder = d / "characters"
    wanted = {slug(n): n for n in every}
    for file_slug, name in sorted(wanted.items()):
        profile = folder / f"{file_slug}.md"
        if not profile.is_file():
            found.append(f"{name}: no profile at characters/{file_slug}.md")
            continue
        body = profile.read_text(encoding="utf-8")
        if TODO in body:
            found.append(f"characters/{file_slug}.md still has the TODO line")
        for pattern, label in ((EMOJI, "Emoji"), (HEX, "Color (#rrggbb)"), (SPEAKS, "Speaks")):
            if not pattern.search(body):
                found.append(f"characters/{file_slug}.md: missing the {label} line")
    if folder.is_dir():
        for profile in sorted(folder.glob("*.md")):
            if profile.stem not in wanted:
                found.append(f"characters/{profile.name} belongs to no character in the roster")
    return found


def listing_problems(bar):
    """Is the bar in hooks/bars.ts and in the Bar setting's options?"""
    found = []
    bars_ts = PLUGIN / "hooks" / "bars.ts"
    text = bars_ts.read_text(encoding="utf-8") if bars_ts.is_file() else ""
    if f"'../bars/{bar}/roster'" not in text or not re.search(rf"^  '{re.escape(bar)}': bar\d+,$", text, re.M):
        found.append("missing from hooks/bars.ts")
    options = read_json(PLUGIN / ".claude-plugin" / "plugin.json")["userConfig"]["bar"]["options"]
    if bar not in options:
        found.append("missing from the Bar setting's options in .claude-plugin/plugin.json")
    return found


def run_checks():
    """The plugin checker and the plugin's tests, once for the whole plugin."""
    if os.environ.get("TOVAR_MODS_SKIP_CHECKS"):
        return []
    if not shutil.which("claude"):
        return ["claude is not on PATH, so the plugin checker and tests did not run"]
    found = []
    r = subprocess.run(["claude", "plugin", "validate", str(PLUGIN)], capture_output=True, text=True)
    output = (r.stdout + r.stderr).strip()
    if r.returncode != 0 or "\u26a0" in output or "\u2718" in output:
        found.append(f"plugin checker:\n{output}")
    if any((PLUGIN / "tests").glob("*.test.*")):
        r = subprocess.run(["claude", "plugin", "test", str(PLUGIN)], capture_output=True, text=True)
        if r.returncode != 0:
            found.append(f"tests:\n{(r.stdout + r.stderr).strip()}")
    return found


def cmd_check(args):
    names = args or bar_names()
    if not names:
        sys.exit("No bars found.")
    failed = False
    for name in names:
        d = BARS / name
        if not d.is_dir():
            print(f"{name}: not found")
            failed = True
            continue
        found = roster_problems(d) + listing_problems(name)
        if found:
            print(f"{name}:")
            for p in found:
                print(f"  - {p}")
            failed = True
        else:
            print(f"{name}: OK")
    found = run_checks()
    if found:
        print("tovar-mods:")
        for p in found:
            print(f"  - {p}")
        failed = True
    sys.exit(1 if failed else 0)


COMMANDS = {"new": cmd_new, "register": cmd_register, "check": cmd_check, "overlap": cmd_overlap}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](sys.argv[2:])
