"""The older self-checks are written for v3.6c's mind and body: they run with v4.0's parts off (each v4.0 part has a
check of its own with it on)."""
V4 = ("traits", "needs4", "opinions", "talk", "ladder", "health", "brain4", "planner", "visitor4")


def v36(cfg):
    for part in V4:
        cfg.setdefault(part, {})["on"] = False
    return cfg
