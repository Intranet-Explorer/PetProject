"""A pet's persistent memory (SPEC §8): the append-only journal, its beliefs, and self."""
import json
from pathlib import Path

MAX_ACTIVE = 20


class Memory:
    def __init__(self, directory, db=None, pet_id=""):
        self.dir, self.db, self.pet_id = Path(directory), db, pet_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "beliefs.json"
        self.beliefs = json.loads(self.path.read_text()) if self.path.exists() else []
        self.things_path = self.dir / "things.json"   # the catalog: every thing it ever made (SPEC-v2 §4)
        self.things = json.loads(self.things_path.read_text()) if self.things_path.exists() else []

    def thing(self, name):
        return next(t for t in reversed(self.things) if t["name"] == name)

    def thing_made(self, name, recipe, tile, tick, by="pet"):
        self.things.append({"name": name, "recipe": recipe, "tile": list(tile), "made": tick, "by": by,
                            "uses": 0, "effects": [], "gone": None})
        self.things_path.write_text(json.dumps(self.things, indent=1))

    def thing_used(self, name, change):
        """Engine truth about what a use did to the needs; never shown to the pet."""
        t = self.thing(name)
        t["uses"], t["effects"] = t["uses"] + 1, (t["effects"] + [change])[-50:]
        self.things_path.write_text(json.dumps(self.things, indent=1))

    def thing_gone(self, name, tick, how):
        self.thing(name)["gone"] = [tick, how]
        self.things_path.write_text(json.dumps(self.things, indent=1))

    def update_self(self, **facts):
        path = self.dir / "self.json"
        me = json.loads(path.read_text()) if path.exists() else {}
        path.write_text(json.dumps({**me, **facts}, indent=1))

    def journal(self, rec):
        with (self.dir / "journal.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")

    def active(self):
        return [b for b in self.beliefs if b["status"] == "active"]

    def is_active(self, bid):
        return any(b["id"] == bid for b in self.active())

    def top(self, n=8):
        """What goes into the perception packet, most recently touched first."""
        return sorted(self.active(), key=lambda b: -b["revised"])[:n]

    def write(self, statement, tick):
        if len(self.active()) >= MAX_ACTIVE:
            return None
        b = {"id": "b%d" % (len(self.beliefs) + 1), "statement": statement,
             "created": tick, "revised": tick, "status": "active"}
        self.beliefs.append(b)
        self._save(b, "write", tick)
        return b["id"]

    def revise(self, bid, statement, tick):
        b = next(b for b in self.beliefs if b["id"] == bid)
        b["revised"] = tick
        if statement.lower() == "discard":
            b["status"] = "discarded"   # stays in the file; history is never deleted
        else:
            b["statement"] = statement
        self._save(b, "discard" if b["status"] == "discarded" else "revise", tick)

    def _save(self, b, op, tick):
        self.path.write_text(json.dumps(self.beliefs, indent=1))
        if self.db:
            self.db.execute("INSERT INTO beliefs_history VALUES (?,?,?,?,?)",
                            (self.pet_id, tick, b["id"], op, b["statement"]))
            self.db.commit()
