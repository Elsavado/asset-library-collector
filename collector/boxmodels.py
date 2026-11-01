"""3D models for the Box account: Objaverse 1.0 .glb files (Sketchfab), each under 250 MB (Box free-plan file
limit), filed by Sketchfab category. Shards are taken from the last one backwards, so these are models the
Drive collection (which goes from the first shard forwards) does not have."""
import gzip
import json

from .common import get, safe, session
from .models import OBJA
from .util import download

CAP = 250 * 10 ** 6


def box_models(sink, st):
    s = session()
    pos = st.setdefault("box", {"shard": 0, "i": 0})
    r = get(s, f"{OBJA}/object-paths.json.gz")
    if not r:
        return 0
    shards = {}
    for uid, p in json.loads(gzip.decompress(r.content)).items():
        shards.setdefault(p.split("/")[1], []).append((uid, p))
    order = sorted(shards, reverse=True)
    n = 0
    while pos["shard"] < len(order) and not sink.full():
        shard = order[pos["shard"]]
        m = get(s, f"{OBJA}/metadata/{shard}.json.gz")
        meta = json.loads(gzip.decompress(m.content)) if m else {}
        objs = sorted(shards[shard])
        while pos["i"] < len(objs) and not sink.full():
            uid, p = objs[pos["i"]]
            pos["i"] += 1
            md = meta.get(uid) or {}
            cats = md.get("categories") or []
            cat = safe(cats[0].get("name") if cats and isinstance(cats[0], dict) else "Uncategorised", 50)
            name = safe(md.get("name") or uid, 70)
            if download(s, f"{OBJA}/{p}", CAP, sink, f"{cat}/{name} {uid[:8]}.glb", lambda h: h[:4] == b"glTF"):
                n += 1
        if pos["i"] >= len(objs):
            pos["shard"], pos["i"] = pos["shard"] + 1, 0
    return n


SOURCES = {"box_models": box_models}
