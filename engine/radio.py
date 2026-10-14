"""The radio (SPEC-v3.1 §5; SPEC-v3.5.1 §5): a real station. The page plays its stream for Tyler; the engine asks the
station, on an allowlist, what song is on, at most once a minute while the radio is on; a pet never fetches anything
and no pet action carries a word out of the house. What comes in is cleaned to plain text, and a pet is told the
kind of music and the song's name. (Until 13 October 2026 it spoke scraps of news, the forecast and "on this day".)"""
import datetime
import json
import logging
import re
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

WMO = {0: "clear skies", 1: "mostly clear", 2: "some cloud", 3: "grey skies", 45: "fog", 48: "freezing fog", 51: "light drizzle", 53: "drizzle",
       55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain", 71: "light snow",
       73: "snow", 75: "heavy snow", 77: "snow grains", 80: "showers", 81: "showers", 82: "violent showers", 85: "snow showers",
       86: "heavy snow showers", 95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with hail"}
STATIC = "the box hisses and crackles, and says nothing you can make out"


def clean(text, cfg, limit=None):
    """Plain text, one line: no markup, no addresses, no quote marks that could close the quotation it is shown in,
    nothing that could pass for a line of the engine's own, nothing with a word on Tyler's blocklist. None if
    there is nothing left to say."""
    from .life import last_sentence
    t = re.sub(r"(?s)<[^>]+>", " ", str(text))
    t = re.sub(r"\b(?:https?://|www\.)\S+", "", t)
    t = re.sub(r"\[[^\]]{0,12}\]", "", t)                   # footnote marks
    t = re.sub(r"[\"“”«»\r\n\t|{}<>]", " ", t).replace("`", "'")
    t = re.sub(r"\s+", " ", t).strip(" -:;,")
    if not t or any(re.search(r"\b%s\b" % re.escape(w), t, re.I) for w in cfg["radio"]["blocklist"]):
        return None
    return last_sentence(t, limit or cfg["radio"]["max_chars"])


def allowed(url, cfg):
    u = urlparse(url)
    return u.scheme == "https" and u.hostname in cfg["radio"]["allow"]


def get(url, cfg, opener=urllib.request.urlopen):
    """The one place the radio touches the network. A host that is not on the allowlist is never asked."""
    if not allowed(url, cfg):
        raise PermissionError("not on the radio's allowlist: %s" % urlparse(url).hostname)
    req = urllib.request.Request(url, headers={"User-Agent": "pet-house-radio/3.1 (a toy; one request an hour)"})
    with opener(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def station(house, cfg):
    """The station their radio is tuned to (SPEC-v3.5.1 §5): the one chosen last, else the first."""
    S = {x["id"]: x for x in cfg["radio"]["stations"]}
    return S.get(house.get("radio", {}).get("station")) or cfg["radio"]["stations"][0]


def now_playing(cfg, directory, st, now=None, fetch=get):
    """The engine (never a pet) asks the station what it is playing, at most once a minute, and keeps it in
    `directory`/now.json; the whole reply goes into fetched.log. None if it cannot be had (it plays all the same)."""
    directory, now = Path(directory), now or time.time()
    directory.mkdir(parents=True, exist_ok=True)
    cache = directory / "now.json"
    had = json.loads(cache.read_text()) if cache.exists() else {}
    if had.get("station") == st["id"] and now - had.get("at", 0) < cfg["radio"]["fetch_seconds"]:
        return had.get("song")
    url = cfg["radio"]["now_url"].format(chan=st["chan"])
    try:
        raw = fetch(url, cfg)
        d = json.loads(raw)
        song = {"artist": clean(d.get("artist") or "", cfg, 80), "title": clean(d.get("title") or "", cfg, 120)}
        song = song if song["title"] else None
    except PermissionError:
        raise
    except Exception as e:
        logging.warning("radio: %s not available: %r", st["id"], e)
        raw, song = "FAILED %r" % e, had.get("song") if had.get("station") == st["id"] else None
    with (directory / "fetched.log").open("a") as f:
        f.write(json.dumps({"at": now, "source": st["id"], "url": url, "raw": raw}) + "\n")
    cache.write_text(json.dumps({"at": now, "station": st["id"], "song": song}))
    return song


def song_words(song):
    return '"%s"%s' % (song["title"], " by " + song["artist"] if song.get("artist") else "") if song else None


def boxes(house):
    return [(room, n, o) for room in house["rooms"].values() if room["type"] for n, o in room["objects"].items() if o.get("fix", {}).get("radio")]


def is_on(house):
    return any(o["state"] == "on" for _, _, o in boxes(house))


def playing(house, cfg, rid):
    """The station playing in this room, or None."""
    return station(house, cfg) if any(room["id"] == rid and o["state"] == "on" for room, _, o in boxes(house)) else None


def tick(house, cfg, song):
    """While their radio is on it plays the station: whoever is in the room hears what kind of music it is, and the
    song's name each time a new one begins (physics feels the music; a body may dance to it)."""
    st = house.setdefault("radio", {"next": 0, "told": [], "said": []})
    S = station(house, cfg)
    on = sorted("%s|%s" % (room["id"], name) for room, name, o in boxes(house) if o["state"] == "on")
    key = [S["id"], (song or {}).get("title")] if on else None
    if key == st.get("heard"):
        return
    fresh = set(on) - set(st.get("on", [])) or (st.get("heard") or [None])[0] != S["id"]
    st["on"], st["heard"] = on, key
    for room, name, o in boxes(house):
        if o["state"] != "on":
            continue
        words = "the radio is playing something %s%s" % (S["sound"], ": " + song_words(song) if song else "")
        rec = {"tick": house["tick"], "room": room["id"], "source": S["id"], "text": song_words(song) or S["sound"]}
        house.setdefault("fresh_radio", []).append(rec)
        for p in house["pets"].values():
            if p["room"] == room["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"]:
                if song:
                    p.setdefault("box", []).insert(0, {"tick": house["tick"], "text": "%s, %s" % (song_words(song), S["sound"])})
                    del p["box"][cfg["radio"]["keep"]:]
                if fresh:
                    p["news"].append("heard")
                p["events"].append([house["tick"], words])


def visitor(house, cfg, room, on, plays):
    """The Radio control (SPEC-v3.3 §3.2; SPEC-v3.5.1 §5: `plays` is a station). Once the pets have found their box,
    this turns THEIR box on or off, wherever it is, and tunes it. Before that it is the visitor's own little radio,
    set down in the room being looked at. Returns the room the box is in. Pets can still switch theirs themselves."""
    from .world import add_event, free_tile
    st = house.setdefault("radio", {"next": 0, "told": [], "said": []})
    if plays in [x["id"] for x in cfg["radio"]["stations"]]:
        st["station"] = plays
    theirs = [(r, n, o) for r, n, o in boxes(house) if n != "little radio"]
    if not theirs:   # the visitor's own: set down where the visitor is looking while it plays, taken away when it is switched off
        for r in house["rooms"].values():
            if r["type"] and (r is not room or not on):
                r["objects"].pop("little radio", None)
        if on and "little radio" not in room["objects"]:
            room["objects"]["little radio"] = {"pos": free_tile(house, cfg, room, [cfg["W"] // 2, 1]), "state": "off",
                                               "fix": {"radio": True, "movable": True, "states": ["off", "on"], "visitor": True}}
        theirs = [(room, "little radio", room["objects"]["little radio"])] if "little radio" in room["objects"] else []
    for r, n, o in theirs:
        if (o["state"] == "on") != bool(on):
            o["state"] = "on" if on else "off"
            for p in house["pets"].values():
                if p["room"] == r["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"]:
                    add_event(house, p, "the visitor turned the radio %s" % ("on" if on else "off"))
                    p["news"].append("visitor")
    return theirs[0][0]["id"] if theirs else None


def off(house):
    """The visitor's mute switch: every box in the house is switched off, not just made quiet (§5.3)."""
    for _, _, o in boxes(house):
        o["state"] = "off"
