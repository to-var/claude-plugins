#!/usr/bin/env python3
"""tovar-shell tmux menu, shown inside display-popup and drawn from skin.json.

Usage: menu.py <pane_id> <window_id> <session_id>
"""
import curses
import json
import locale
import math
import os
import shlex
import shutil
import subprocess
import sys

PANE, WIN, SESS = sys.argv[1:4]
CLIENT = sys.argv[4] if len(sys.argv) > 4 else ""
TOOLS_FILE = os.path.expanduser("~/.config/tmux/tovar-tools.json")

BORDERS = {
    "single": "┌┐└┘─│",
    "double": "╔╗╚╝═║",
    "rounded": "╭╮╰╯─│",
    "heavy": "┏┓┗┛━┃",
}

DEFAULT_SKIN = {
    "colors": {"bg": 18, "text": 231, "dim": 245, "accent": 226, "select_bg": 25,
               "select_fg": 226, "head": 117},
    "menu": {"layout": "buttons", "border": "single", "border_selected": "double",
             "cursor": "▶", "title": "COMMAND", "title_format": "◆  {}  ◆",
             "spaced": True, "upper": True, "rule": "═"},
}


def load_skin():
    skin = json.loads(json.dumps(DEFAULT_SKIN))
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "skin.json"),
                  encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return skin
    for part in ("colors", "menu"):
        if isinstance(data.get(part), dict):
            skin[part].update(data[part])
    return skin


SKIN = load_skin()
MENU = SKIN["menu"]
NORMAL = BORDERS.get(MENU["border"], BORDERS["single"])
SELECTED = BORDERS.get(MENU["border_selected"], BORDERS["double"])
CURSOR = MENU["cursor"]


def label_of(text):
    return text.upper() if MENU["upper"] else text


# color pair ids
TEXT, SEL, HEAD, DIM, GOOD, GOLD = 1, 2, 3, 4, 5, 6
A = {}

main_cursor = 0


def tm(*a):
    return subprocess.run(["tmux", *a], capture_output=True, text=True).stdout


def run(*a):
    subprocess.run(["tmux", *a], capture_output=True)


def get_panes(win):
    fmt = ("#{pane_id}|#{pane_index}|#{pane_left}|#{pane_top}|#{pane_width}|"
           "#{pane_height}|#{pane_active}|#{pane_current_command}|#{pane_current_path}")
    out = []
    for line in tm("list-panes", "-t", win, "-F", fmt).splitlines():
        f = line.split("|", 8)
        if len(f) < 9:
            continue
        out.append(dict(id=f[0], idx=f[1], l=int(f[2]), t=int(f[3]), w=int(f[4]),
                        h=int(f[5]), act=f[6] == "1", cmd=f[7],
                        path=os.path.basename(f[8].rstrip("/")) or "/"))
    return out


def get_windows():
    fmt = "#{window_id}|#{window_index}|#{window_name}|#{window_zoomed_flag}"
    out = []
    for line in tm("list-windows", "-t", SESS, "-F", fmt).splitlines():
        f = line.split("|", 3)
        if len(f) < 4:
            continue
        out.append(dict(id=f[0], idx=f[1], name=f[2], zoom=f[3] == "1"))
    return out


def get_sessions():
    fmt = "#{session_id}|#{session_name}|#{session_windows}|#{session_attached}"
    out = []
    for line in tm("list-sessions", "-F", fmt).splitlines():
        f = line.split("|", 3)
        if len(f) == 4:
            out.append(dict(id=f[0], name=f[1], windows=int(f[2]), attached=int(f[3])))
    return out


# ---------- drawing helpers ----------

def put(scr, y, x, s, attr):
    h, w = scr.getmaxyx()
    if y < 0 or y >= h or x >= w or not s:
        return
    if x < 0:
        s = s[-x:]
        x = 0
    s = s[: w - x]
    try:
        scr.addstr(y, x, s, attr)
    except curses.error:
        pass


def rect(scr, y, x, h, w, attr, dbl=False, fill=None, label=None, lattr=None):
    if h < 2 or w < 2:
        return
    c = SELECTED if dbl else NORMAL
    if fill is not None:
        for r in range(y + 1, y + h - 1):
            put(scr, r, x + 1, " " * (w - 2), fill)
    put(scr, y, x, c[0] + c[4] * (w - 2) + c[1], attr)
    put(scr, y + h - 1, x, c[2] + c[4] * (w - 2) + c[3], attr)
    for r in range(y + 1, y + h - 1):
        put(scr, r, x, c[5], attr)
        put(scr, r, x + w - 1, c[5], attr)
    if label and w > 4:
        put(scr, y, x + 2, label[: w - 4], lattr or attr)


def center_text(scr, y, s, attr):
    _, w = scr.getmaxyx()
    put(scr, y, max(0, (w - len(s)) // 2), s, attr)


def frame(scr, title, hint):
    h, w = scr.getmaxyx()
    scr.erase()
    title = label_of(title)
    if MENU["spaced"]:
        title = "  ".join(title)
    center_text(scr, 0, MENU["title_format"].format(title), A[GOLD] | curses.A_BOLD)
    put(scr, 1, 0, MENU["rule"] * w, A[TEXT])
    put(scr, h - 2, 0, MENU["rule"] * w, A[TEXT])
    put(scr, h - 1, 1, hint[: w - 2], A[DIM])
    return h, w


def move(rects, cur, d):
    """Pick the neighbour of rects[cur] in direction d (L R U D)."""
    cx, cy = rects[cur]
    best, best_i = None, cur
    for i, (x, y) in enumerate(rects):
        if i == cur:
            continue
        dx, dy = x - cx, y - cy
        if d == "L" and dx < 0:
            p, q = -dx, abs(dy)
        elif d == "R" and dx > 0:
            p, q = dx, abs(dy)
        elif d == "U" and dy < 0:
            p, q = -dy, abs(dx)
        elif d == "D" and dy > 0:
            p, q = dy, abs(dx)
        else:
            continue
        sc = p + 2 * q
        if best is None or sc < best:
            best, best_i = sc, i
    return best_i


def read_key(scr):
    k = scr.getch()
    if k in (curses.KEY_LEFT, ord("h")):
        return "L"
    if k in (curses.KEY_RIGHT, ord("l")):
        return "R"
    if k in (curses.KEY_UP, ord("k")):
        return "U"
    if k in (curses.KEY_DOWN, ord("j")):
        return "D"
    if k in (10, 13, curses.KEY_ENTER):
        return "ENTER"
    if k in (27, ord("q"), curses.KEY_BACKSPACE, 127, 8):
        return "BACK"
    if k == curses.KEY_RESIZE:
        return "RESIZE"
    if 32 <= k < 127:
        return chr(k)
    return None


def draw_map(scr, panes, oy, ox, ah, aw, sel_id, big):
    """Draw a scaled miniature of a window's pane layout."""
    if not panes:
        return
    ww = max(p["l"] + p["w"] for p in panes)
    wh = max(p["t"] + p["h"] for p in panes)
    s = min(aw / (ww + 1), ah / (wh + 1))
    mw, mh = int((ww + 1) * s), int((wh + 1) * s)
    ox += (aw - mw) // 2
    oy += (ah - mh) // 2

    def geom(p):
        x0 = int(p["l"] * s)
        x1 = int((p["l"] + p["w"] + 1) * s)
        y0 = int(p["t"] * s)
        y1 = int((p["t"] + p["h"] + 1) * s)
        return oy + y0, ox + x0, max(3, y1 - y0 + 1), max(4, x1 - x0 + 1)

    order = [p for p in panes if p["id"] != sel_id] + [p for p in panes if p["id"] == sel_id]
    for p in order:
        y, x, h, w = geom(p)
        chosen = p["id"] == sel_id
        if big:
            label = " %s %s%s " % (p["idx"], p["cmd"], " ●" if p["act"] else "")
            if chosen:
                rect(scr, y, x, h, w, A[GOLD] | curses.A_BOLD, dbl=True, fill=A[SEL], label=label,
                     lattr=A[SEL] | curses.A_BOLD)
                if h >= 4:
                    put(scr, y + 2, x + 2, p["path"][: w - 4], A[SEL])
            else:
                rect(scr, y, x, h, w, A[TEXT], label=label, lattr=A[HEAD])
                if h >= 4:
                    put(scr, y + 2, x + 2, p["path"][: w - 4], A[DIM])
        else:
            attr = A[GOLD] if p["act"] else A[DIM]
            rect(scr, y, x, h, w, attr)


def choices(scr, h, w, names, cur):
    """Draw the vertical choice list in the skin's layout."""
    if MENU["layout"] == "list" or len(names) * 3 > h - 6:
        bw = max(30, max(len(n) for n in names) + 10)
        gap = 2 if len(names) * 2 + 1 <= h - 6 else 1
        bh = len(names) * gap + 1
        x = (w - bw) // 2
        y = max(3, (h - bh) // 2)
        rect(scr, y, x, bh, bw, A[TEXT])
        for i, name in enumerate(names):
            row = y + 1 + i * gap
            if i == cur:
                put(scr, row, x + 1, " " * (bw - 2), A[SEL])
                put(scr, row, x + 2, CURSOR, A[SEL] | curses.A_BOLD)
                put(scr, row, x + 4, label_of(name), A[SEL] | curses.A_BOLD)
            else:
                put(scr, row, x + 4, label_of(name), A[TEXT])
        return
    bw = 30
    x = (w - bw) // 2
    step = 4 if len(names) * 4 <= h - 6 else 3
    top = max(3, (h - len(names) * step) // 2)
    for i, name in enumerate(names):
        y = top + i * step
        name = label_of(name)
        if i == cur:
            rect(scr, y, x, 3, bw, A[GOLD] | curses.A_BOLD, dbl=True, fill=A[SEL])
            put(scr, y + 1, x + (bw - len(name)) // 2, name, A[SEL] | curses.A_BOLD)
            put(scr, y + 1, x - 3, CURSOR, A[GOLD] | curses.A_BOLD)
        else:
            rect(scr, y, x, 3, bw, A[TEXT])
            put(scr, y + 1, x + (bw - len(name)) // 2, name, A[TEXT])


# ---------- screens ----------

def main_screen(scr):
    global main_cursor
    items = [("Windows", "win", "Switch between windows"),
             ("Panes", "pane", "Pick a pane in this window"),
             ("Sessions", "sessions", "Switch, create, rename and close sessions"),
             ("Layouts", "layouts", "Rearrange the panes of this window"),
             ("Tools", "tools", "Scratch terminal, monitor, disk space, logs"),
             ("System", "system", "Copy mode, reload, detach")]
    while True:
        h, w = frame(scr, MENU["title"], "↑↓ Move    Enter Select    Esc Close")
        choices(scr, h, w, [name for name, _, _ in items], main_cursor)
        center_text(scr, h - 4, items[main_cursor][2], A[HEAD])
        scr.refresh()
        k = read_key(scr)
        if k == "U":
            main_cursor = (main_cursor - 1) % len(items)
        elif k == "D":
            main_cursor = (main_cursor + 1) % len(items)
        elif k == "ENTER":
            return items[main_cursor][1]
        elif k == "BACK":
            return None


def pane_screen(scr):
    panes = get_panes(WIN)
    if not panes:
        return "main"
    cur = next((i for i, p in enumerate(panes) if p["id"] == PANE), 0)
    centers = [(p["l"] + p["w"] / 2, (p["t"] + p["h"] / 2) * 2) for p in panes]
    while True:
        h, w = frame(scr, "Panes", "←↑↓→ Move   Enter Switch   | Split right   - Split below   z Zoom   x Close   Esc Back")
        draw_map(scr, panes, 3, 2, h - 6, w - 4, panes[cur]["id"], big=True)
        scr.refresh()
        k = read_key(scr)
        pid = panes[cur]["id"]
        if k in ("L", "R", "U", "D"):
            cur = move(centers, cur, k)
        elif k == "ENTER":
            run("select-pane", "-t", pid)
            return None
        elif k == "BACK":
            return "main"
        elif k in ("|", "v"):
            run("split-window", "-h", "-t", pid, "-c", "#{pane_current_path}")
            return None
        elif k == "-":
            run("split-window", "-v", "-t", pid, "-c", "#{pane_current_path}")
            return None
        elif k == "z":
            run("resize-pane", "-Z", "-t", pid)
            return None
        elif k == "x":
            run("kill-pane", "-t", pid)
            return None


def prompt(scr, label, text):
    curses.curs_set(1)
    buf = text
    while True:
        h, w = scr.getmaxyx()
        put(scr, h - 1, 0, " " * (w - 1), A[TEXT])
        put(scr, h - 1, 1, label + buf, A[GOLD])
        scr.refresh()
        k = scr.getch()
        if k in (10, 13, curses.KEY_ENTER):
            curses.curs_set(0)
            return buf
        if k == 27:
            curses.curs_set(0)
            return None
        if k in (curses.KEY_BACKSPACE, 127, 8):
            buf = buf[:-1]
        elif 32 <= k < 127:
            buf += chr(k)


TILE_W, TILE_H = 26, 11


def tile_grid(scr, h, w, tiles, cur):
    """Draw tiles (label, panes, here) in a grid with the selected one highlighted."""
    cols = max(1, (w - 2) // (TILE_W + 1))
    rows_vis = max(1, (h - 5) // TILE_H)
    grid = [(i % cols, i // cols) for i in range(len(tiles))]
    first = max(0, grid[cur][1] - rows_vis + 1)
    for i, t in enumerate(tiles):
        c, r = grid[i]
        if r < first or r >= first + rows_vis:
            continue
        x = 2 + c * (TILE_W + 1)
        y = 3 + (r - first) * TILE_H
        label = " %s%s " % (t["label"][: TILE_W - 8], " ●" if t.get("here") else "")
        if i == cur:
            rect(scr, y, x, TILE_H - 1, TILE_W, A[GOLD] | curses.A_BOLD, dbl=True, fill=A[SEL],
                 label=label, lattr=A[SEL] | curses.A_BOLD)
        else:
            rect(scr, y, x, TILE_H - 1, TILE_W, A[TEXT], label=label, lattr=A[HEAD])
        draw_map(scr, t["panes"], y + 2, x + 2, TILE_H - 5, TILE_W - 4, None, big=False)
    return grid


def confirm(scr, question):
    h, w = scr.getmaxyx()
    put(scr, h - 1, 0, " " * (w - 1), A[TEXT])
    put(scr, h - 1, 1, question + " (y/n)", A[GOLD] | curses.A_BOLD)
    scr.refresh()
    return scr.getch() in (ord("y"), ord("Y"))


def win_screen(scr):
    def build():
        return [dict(id=x["id"], label="%s:%s%s" % (x["idx"], x["name"], " Z" if x["zoom"] else ""),
                     here=x["id"] == WIN, name=x["name"], panes=get_panes(x["id"]))
                for x in get_windows()]
    wins = build()
    if not wins:
        return "main"
    cur = next((i for i, x in enumerate(wins) if x["id"] == WIN), 0)
    while True:
        h, w = frame(scr, "Windows", "←↑↓→ Move   Enter Switch   n New   r Rename   x Close   Esc Back")
        grid = tile_grid(scr, h, w, wins, cur)
        scr.refresh()
        k = read_key(scr)
        if k in ("L", "R", "U", "D"):
            cur = move(grid, cur, k)
        elif k == "ENTER":
            run("select-window", "-t", wins[cur]["id"])
            return None
        elif k == "BACK":
            return "main"
        elif k == "n":
            run("new-window", "-t", SESS)
            return None
        elif k == "x":
            run("kill-window", "-t", wins[cur]["id"])
            return None
        elif k == "r":
            name = prompt(scr, "Rename window: ", wins[cur]["name"])
            if name:
                run("rename-window", "-t", wins[cur]["id"], name)
                run("set-window-option", "-t", wins[cur]["id"], "automatic-rename", "off")
                wins = build()


def sessions_screen(scr):
    def build():
        return [dict(id=x["id"], label="%s  %d win" % (x["name"], x["windows"]),
                     here=x["id"] == SESS, name=x["name"], panes=get_panes(x["id"]))
                for x in get_sessions()]
    sessions = build()
    if not sessions:
        return "main"
    cur = next((i for i, x in enumerate(sessions) if x["id"] == SESS), 0)
    while True:
        h, w = frame(scr, "Sessions", "←↑↓→ Move   Enter Switch   n New   r Rename   x Close   Esc Back")
        grid = tile_grid(scr, h, w, sessions, cur)
        scr.refresh()
        k = read_key(scr)
        sid = sessions[cur]["id"]
        if k in ("L", "R", "U", "D"):
            cur = move(grid, cur, k)
        elif k == "ENTER":
            run("switch-client", *(["-c", CLIENT] if CLIENT else []), "-t", sid)
            return None
        elif k == "BACK":
            return "main"
        elif k == "n":
            name = prompt(scr, "New session name: ", "")
            if name:
                run("new-session", "-d", "-s", name)
                run("switch-client", *(["-c", CLIENT] if CLIENT else []), "-t", name)
                return None
        elif k == "r":
            name = prompt(scr, "Rename session: ", sessions[cur]["name"])
            if name:
                run("rename-session", "-t", sid, name)
                sessions = build()
        elif k == "x":
            warn = " (this is your current one)" if sessions[cur]["here"] else ""
            if confirm(scr, "Close session %s%s?" % (sessions[cur]["name"], warn)):
                run("kill-session", "-t", sid)
                return None


# Layouts: tmux names, a label, and a sketch of where the panes go.
LAYOUTS = [("even-horizontal", "Side by side"), ("even-vertical", "Stacked"),
           ("main-vertical", "Big left"), ("main-horizontal", "Big top"), ("tiled", "Tiled grid")]


def sketch(name, n):
    """Fake panes for a 100x30 window laid out the way tmux would."""
    vw, vh = 100, 30
    out = []

    def add(l, t, w, h):
        out.append(dict(id=str(len(out)), idx=str(len(out)), l=l, t=t, w=w, h=h,
                        act=not out, cmd="", path=""))

    def split(total, parts):
        size = (total - (parts - 1)) // parts
        return [(i * (size + 1), size) for i in range(parts)]

    if name == "even-horizontal":
        for l, w in split(vw, n):
            add(l, 0, w, vh)
    elif name == "even-vertical":
        for t, h in split(vh, n):
            add(0, t, vw, h)
    elif name == "main-vertical":
        add(0, 0, 60, vh)
        for t, h in split(vh, n - 1):
            add(61, t, vw - 61, h)
    elif name == "main-horizontal":
        add(0, 0, vw, 17)
        for l, w in split(vw, n - 1):
            add(l, 18, w, vh - 18)
    else:
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        xs, ys = split(vw, cols), split(vh, rows)
        for i in range(n):
            (l, w), (t, h) = xs[i % cols], ys[i // cols]
            add(l, t, w, h)
    return out


def layouts_screen(scr):
    count = len(get_panes(WIN))
    usable = count >= 2
    tiles = [dict(label=label, panes=sketch(name, max(count, 3)), name=name) for name, label in LAYOUTS]
    cur = 0
    while True:
        hint = ("←↑↓→ Move   Enter Apply   r Rotate panes   Esc Back" if usable
                else "Split a pane first: layouts need 2 or more panes.   Esc Back")
        h, w = frame(scr, "Layouts", hint)
        grid = tile_grid(scr, h, w, tiles, cur)
        scr.refresh()
        k = read_key(scr)
        if k in ("L", "R", "U", "D"):
            cur = move(grid, cur, k)
        elif k == "ENTER" and usable:
            run("select-layout", "-t", WIN, tiles[cur]["name"])
            return None
        elif k == "r" and usable:
            run("rotate-window", "-t", WIN)
            return None
        elif k == "BACK":
            return "main"


def tool_list():
    """(name, shell command, wait for Enter at the end). Your own come from tovar-tools.json."""
    shell = shlex.quote(os.environ.get("SHELL") or "sh")
    tools = [("Scratch terminal", "exec " + shell, False)]
    monitor = shutil.which("htop") or shutil.which("top")
    if monitor:
        tools.append(("System monitor", os.path.basename(monitor), False))
    tools.append(("Disk space", "df -h -x tmpfs -x devtmpfs -x squashfs -x overlay", True))
    if shutil.which("journalctl"):
        tools.append(("System log", "journalctl -n 500 --no-pager | less +G", False))
    if shutil.which("ss"):
        tools.append(("Listening ports", "ss -tulpn", True))
    try:
        with open(TOOLS_FILE, encoding="utf-8") as f:
            for item in json.load(f):
                if isinstance(item.get("name"), str) and isinstance(item.get("command"), str):
                    tools.append((item["name"][:24], item["command"], bool(item.get("pause", False))))
    except (OSError, ValueError, AttributeError):
        pass
    return tools


def tools_screen(scr):
    tools = tool_list()
    cur = 0
    while True:
        h, w = frame(scr, "Tools", "↑↓ Move    Enter Open    Esc Back")
        choices(scr, h, w, [t[0] for t in tools], cur)
        if not CLIENT:
            center_text(scr, h - 4, "Reapply the skin: this menu was opened without a client.", A[HEAD])
        scr.refresh()
        k = read_key(scr)
        if k == "U":
            cur = (cur - 1) % len(tools)
        elif k == "D":
            cur = (cur + 1) % len(tools)
        elif k == "BACK":
            return "main"
        elif k == "ENTER" and CLIENT:
            name, command, pause = tools[cur]
            if pause:
                command += '; printf "\\nPress Enter to close "; read _'
            start = tm("display-message", "-p", "-t", PANE, "#{pane_current_path}").strip() or os.path.expanduser("~")
            popup = ("sleep 0.3; tmux display-popup -c %s -d %s -E -w 90%% -h 85%% -b %s -T %s -S %s sh -c %s"
                     % (shlex.quote(CLIENT), shlex.quote(start), MENU["border"],
                        shlex.quote(" %s " % name), shlex.quote("fg=colour%d" % SKIN["colors"]["accent"]),
                        shlex.quote(command)))
            subprocess.Popen(["tmux", "run-shell", "-b", popup], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            return None


def system_screen(scr):
    items = [("Copy mode", ("copy-mode", "-t", PANE)),
             ("Reload config", ("source-file", os.path.expanduser("~/.tmux.conf"))),
             ("Send Ctrl+b to pane", ("send-keys", "-t", PANE, "C-b")),
             ("Detach", ("detach-client", "-s", SESS))]
    cur = 0
    while True:
        h, w = frame(scr, "System", "↑↓ Move    Enter Select    Esc Back")
        choices(scr, h, w, [name for name, _ in items], cur)
        scr.refresh()
        k = read_key(scr)
        if k == "U":
            cur = (cur - 1) % len(items)
        elif k == "D":
            cur = (cur + 1) % len(items)
        elif k == "ENTER":
            run(*items[cur][1])
            return None
        elif k == "BACK":
            return "main"


def main(scr):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    c = SKIN["colors"]
    pairs = {TEXT: (c["text"], c["bg"]), SEL: (c["select_fg"], c["select_bg"]),
             HEAD: (c["head"], c["bg"]), DIM: (c["dim"], c["bg"]),
             GOOD: (c["accent"], c["bg"]), GOLD: (c["accent"], c["bg"])}
    for n, (fg, bg) in pairs.items():
        curses.init_pair(n, fg, bg)
        A[n] = curses.color_pair(n)
    scr.bkgd(" ", A[TEXT])
    scr.keypad(True)
    screens = {"main": main_screen, "win": win_screen, "pane": pane_screen, "sessions": sessions_screen,
               "layouts": layouts_screen, "tools": tools_screen, "system": system_screen}
    state = "main"
    while state:
        state = screens[state](scr)


if __name__ == "__main__":
    os.environ.setdefault("ESCDELAY", "25")
    locale.setlocale(locale.LC_ALL, "")
    curses.wrapper(main)
