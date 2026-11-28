"""SPEC-v5.0 §4 (helper B): the machine trades. While [trade] is on (on5) it gives nothing free ([machine] free reads
0: machine.left); it sells the materials it stocks at `[trade] price` scrap-points a bit, and buys bits (1 each) and
made things at their scrap value (items.scrap_value). A hob's scrap is pet["scrap"], a whole number (items.migrate
made it 0; the v3.5.8 count of scrap fed to the Works, which used that key, is kept as pet["scrap_back"]). Selling is
taking the thing to the machine: the body's "feed the machine" and the job's step both come here (machine.feed), and
what is sold is still scrap for the Works (works.fed), so the house store keeps filling the machine's priced stock.
The morning's restock and the visitor's "Stock the machine" are as they were. The live machine's own materials past
the six (wax, resin, string, cloth: the Works built them) are priced in config.toml beside the six, at 1."""
from . import contracts as K
from . import items, machine, things, works
from .world import a as a_bit, add_event, label, moment

PURSE = ["no scrap", "a little scrap", "some scrap", "a good pile of scrap"]   # what a hob is told it has (never a number)


def on(cfg):
    return K.on5(cfg, "trade")


def price(cfg, material):
    return cfg["trade"]["price"].get(material, 1)


def purse(pet):
    """Its scrap-points (an old save's v3.5.8 count, a dict under the same key, moved aside first)."""
    s = pet.get("scrap")
    if not isinstance(s, int):
        if isinstance(s, dict):
            pet["scrap_back"] = s
        pet["scrap"] = s = 0
    return s


def purse_words(pet):
    n = purse(pet)
    return PURSE[0 if n <= 0 else 1 if n < 3 else 2 if n < 8 else 3]


def earn(house, pet, n):
    pet["scrap"] = purse(pet) + n
    K.count(house, "scrap_earned", pet["id"], n)


def buy(house, cfg, pet, material):
    """API5: one bit of a material out of the machine for its price: (words, ok). Only in the machine's room."""
    room = house["rooms"][pet["room"]]
    S = machine.state(house, cfg)
    if not machine.spot(room):
        return "there is no machine here", False
    if S["stock"].get(material, 0) <= 0:
        return "the machine has no %s left" % material, False
    cost = price(cfg, material)
    if purse(pet) < cost:
        return "the machine has %s, but you have %s to pay for it" % (material, "no scrap" if not purse(pet) else "too little scrap"), False
    S["stock"][material] -= 1
    S["used"] = house["tick"]
    pet["scrap"] -= cost
    K.count(house, "scrap_spent", pet["id"], cost)
    machine.got(house, cfg, pet, room, material)
    moment(house, "machine", "%s bought %s from the machine" % (label(pet), material), pet["id"], room["id"])
    return "you paid the machine and it dropped %s into your paws; you have %s left" % (a_bit(material), purse_words(pet)), True


def value(house, cfg, pet, name):
    """What the machine pays for this: a bit it carries, or a made thing here (None: it won't take it, with why)."""
    room = house["rooms"][pet["room"]]
    if name in pet["carrying"]:
        return 1, None
    why = machine.refuses(house, cfg, pet, room, name)
    if why:
        return None, why
    it = items.of(house, cfg, room["objects"][name], name, room)
    return (items.scrap_value(cfg, it) if it else 1), None


def sell(house, cfg, pet, name):
    """API5: a bit it carries, or a made thing here, sold to the machine for scrap: (words, ok). Only in the machine's
    room. A bit of a material the machine stocks goes into its stock; what is sold is scrap for the Works too."""
    room = house["rooms"][pet["room"]]
    if not machine.spot(room):
        return "there is no machine here", False
    n, why = value(house, cfg, pet, name)
    if n is None:
        return why, False
    o = None
    if name in pet["carrying"]:
        pet["carrying"].remove(name)
        if name in cfg["machine"]["materials"]:
            machine.fill(house, cfg, name, 1)
        said = a_bit(name)
    else:
        o = room["objects"].pop(name)
        owner = house["pets"].get(o["made"]["owner"] or "")
        if owner and owner is not pet and owner["stage"] != "dead":
            add_event(house, owner, "%s sold your %s to the machine" % (label(pet), name))
        things.gone(house, o, name, "sold to the machine", room)
        said = "the " + name
    machine.state(house, cfg)["used"] = house["tick"]
    earn(house, pet, n)
    scrap = ""
    if o is not None:
        scrap = works.fed(house, cfg, pet, o)[0]
    else:   # (three bits are one scrap for the Works, as fed)
        pet["sold_bits"] = pet.get("sold_bits", 0) + 1
        if pet["sold_bits"] >= cfg["machine"]["bits"]:
            pet["sold_bits"], scrap = 0, works.fed(house, cfg, pet, None)[0]
    moment(house, "fed", "%s sold %s to the machine" % (label(pet), said), pet["id"], room["id"])
    return "you sold %s to the machine; you have %s now%s" % (said, purse_words(pet), scrap), True


def feed(house, cfg, pet, what):
    """machine.feed while trading: "bits" is three bits it carries sold one by one; else the thing. (text, fx, key)."""
    if what == "bits":
        said = [sell(house, cfg, pet, b)[0] for b in list(pet["carrying"][:cfg["machine"]["bits"]])]
        return (said[-1] if said else "you have no bits to sell"), {}, "machine sell" if said else None
    text, ok = sell(house, cfg, pet, what)
    return text, {}, "machine sell" if ok else None


def sense(house, cfg, pet):
    """The packet's line at the machine while trading (no numbers)."""
    S = machine.state(house, cfg)
    have = [m for m in cfg["machine"]["materials"] if S["stock"].get(m, 0) > 0]
    return ["the machine here sells %s for scrap, and buys bits and made things for scrap; you have %s" % (machine.listed(have), purse_words(pet))] + works.sense(house, cfg, pet)
