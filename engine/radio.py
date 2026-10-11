"""The radio (SPEC-v3.1 §5): a box that speaks scraps of the real outside world. The engine fetches them, from a
short fixed list of sources on an allowlist, at most once an hour each; a pet never fetches anything and no pet
action carries a word out of the house. What comes in is cleaned to plain text and is only ever shown to a pet
quoted, as something the box said."""
import datetime
import json
import logging
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
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


def parse(kind, raw):
    """A source's reply as short things for the box to say."""
    if kind == "forecast":
        d = json.loads(raw)["daily"]
        names = ["Today", "Tomorrow", "The day after"]
        return ["The forecast for the Twin Cities. %s: %s, a high of %d and a low of %d degrees, wind up to %d." % (
            names[i], WMO.get(d["weather_code"][i], "changeable weather"), round(d["temperature_2m_max"][i]), round(d["temperature_2m_min"][i]),
            round(d["wind_speed_10m_max"][i])) for i in range(min(3, len(d["time"])))]
    if kind == "onthisday":
        return ["On this day in %s: %s" % (e["year"], e["text"]) for e in json.loads(raw).get("selected", []) if e.get("text")]
    if kind == "rss":
        out = []
        for item in ET.fromstring(raw).iter("item"):
            title, about = (item.findtext("title") or "").strip(), (item.findtext("description") or "").strip()
            out.append("In the news: %s. %s" % (title.rstrip("."), about) if about else "In the news: " + title)
        return out
    raise ValueError("unknown kind of source: %s" % kind)


def refresh(cfg, directory, now=None, fetch=get):
    """Ask each source that is due, keep what it said in `directory`/<name>.json, and write the whole of every
    reply into fetched.log. A source that fails keeps its old words; with none, the radio plays static."""
    directory, now = Path(directory), now or time.time()
    directory.mkdir(parents=True, exist_ok=True)
    today = datetime.date.fromtimestamp(now)
    for src in cfg["radio"]["sources"]:
        cache = directory / ("%s.json" % re.sub(r"\W+", "-", src["name"]))
        had = json.loads(cache.read_text()) if cache.exists() else {"at": 0, "items": []}
        if now - had["at"] < cfg["radio"]["fetch_minutes"] * 60:
            continue
        url = src["url"].format(month="%02d" % today.month, day="%02d" % today.day)
        try:
            raw = fetch(url, cfg)
            items = [c for c in (clean(x, cfg) for x in parse(src["kind"], raw)) if c]
        except PermissionError:
            raise
        except Exception as e:
            logging.warning("radio: %s not available: %r", src["name"], e)
            raw, items = "FAILED %r" % e, had["items"]
        with (directory / "fetched.log").open("a") as f:
            f.write(json.dumps({"at": now, "source": src["name"], "url": url, "raw": raw}) + "\n")
        cache.write_text(json.dumps({"at": now, "items": items}))
    return items_in(cfg, directory)


def items_in(cfg, directory):
    out = []
    for src in cfg["radio"]["sources"]:
        cache = Path(directory) / ("%s.json" % re.sub(r"\W+", "-", src["name"]))
        if cache.exists():
            out += [{"source": src["name"], "text": t} for t in json.loads(cache.read_text())["items"]]
    return out


def boxes(house):
    return [(room, n, o) for room in house["rooms"].values() if room["type"] for n, o in room["objects"].items() if o.get("fix", {}).get("radio")]


def is_on(house):
    return any(o["state"] == "on" for _, _, o in boxes(house))


def tick(house, cfg, items):
    """While a box is on it says one thing every so often to whoever is in the room, and static if it has nothing."""
    R = cfg["radio"]
    for room, name, o in boxes(house):
        if o["state"] != "on":
            continue
        st = house.setdefault("radio", {"next": 0, "told": [], "said": []})
        if house["tick"] < st["next"]:
            continue
        st["next"] = house["tick"] + max(1, round(R["every_minutes"] * 60 / (cfg["clock"]["tick_seconds"] * cfg["pace"])))
        fresh = [i for i in items if i["text"] not in st["told"]] or items
        pick = fresh[(house["tick"] // 7) % len(fresh)] if fresh else None   # a different source each time, by the clock
        if pick:
            st["told"] = (st["told"] + [pick["text"]])[-300:]
        rec = {"tick": house["tick"], "room": room["id"], "source": pick["source"] if pick else "static", "text": pick["text"] if pick else ""}
        st["said"] = (st["said"] + [rec])[-40:]
        house.setdefault("fresh_radio", []).append(rec)
        for p in house["pets"].values():
            if p["room"] == room["id"] and p["stage"] not in ("egg", "dead") and not p["sleep"]:
                if pick:
                    p.setdefault("box", []).insert(0, {"tick": house["tick"], "text": pick["text"]})
                    del p["box"][R["keep"]:]
                    p["news"].append("heard")
                p["events"].append([house["tick"], 'the box says: "%s"' % pick["text"] if pick else STATIC])


def off(house):
    """The visitor's mute switch: every box in the house is switched off, not just made quiet (§5.3)."""
    for _, _, o in boxes(house):
        o["state"] = "off"
