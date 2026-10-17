"""The rail (SPEC-v3.5.12 §3): a little train the Works builds, running from the machine room through every room on a
track, carrying things to the store and back. Like the sweeper it is a creature, not a pet: it never thinks."""


def view(house, cfg):
    return house.get("rail")


def cart_view(house, cfg):
    tr = next((c for c in house["creatures"] if c["kind"] == "train"), None)
    return [{"name": h["name"], "made": h["o"].get("made")} for h in tr.get("held", [])] if tr else []
