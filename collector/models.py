"""3D models: as many as the Drive holds, in .stl .obj .fbx .3ds .blend .glb (and .dae .gltf .ply).

Sources: Sketchfab models (Objaverse 1.0 mirror), model files in GitHub repositories (Objaverse-XL index),
Thingi10K, the Smithsonian 3D collection, Poly Haven, curated sample sets, and Thingiverse through its official
API when THINGIVERSE_TOKEN is set. Files are filed by format, then by collection or category."""
import gzip
import json
import os
import tarfile
import time
from urllib.parse import quote

from . import split
from .common import get, safe, session
from .util import MODELS, download, fetch_many, gh, gh_file, gh_tree, not_html

HF = "https://huggingface.co/datasets"
OBJA = f"{HF}/allenai/objaverse/resolve/main"
XL = f"{HF}/allenai/objaverse-xl/resolve/main"
CAP = 60 * 2 ** 20  # per model: keeps the count high

FOLDER = {"stl": "STL", "obj": "OBJ", "fbx": "FBX", "3ds": "3DS", "blend": "BLEND", "glb": "GLB", "gltf": "GLTF",
          "dae": "DAE (Collada)", "ply": "PLY", "usdz": "USDZ", "off": "OFF"}
SIDECAR = {"obj": ["mtl"], "gltf": ["bin"]}  # small companion files fetched with the model


def _parquet(s, url, path, columns, filters=None):
    import pyarrow.parquet as pq
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with s.get(url, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(8 << 20):
                    f.write(chunk)
    return pq.read_table(path, columns=columns, filters=filters)


# models each Sketchfab lane adds from 2026-11-02 on (with the GitHub lane the library reaches ~230,000)
# 2026-11-07: the folder cap (301,000 files, CAP_* in the workflow) decides when to stop; these only keep lanes apart
QUOTA = {"sketchfab": 150000, "sketchfab_mid": 150000, "sketchfab_rev": 150000, "github_models": 80000}


def sketchfab(sink, st, lane="sketchfab"):
    """Objaverse 1.0: ~800k Sketchfab models as .glb, filed by Sketchfab category. Three lanes walk the 160
    shards from the start, from the middle and from the end, so they never fetch the same models."""
    s = session()
    pos = st.setdefault("skf", {"shard": 0, "i": 0})
    r = get(s, f"{OBJA}/object-paths.json.gz")
    if not r:
        return 0
    paths = json.loads(gzip.decompress(r.content))
    lv = get(s, f"{OBJA}/lvis-annotations.json.gz")  # LVIS objects belong to the Lintel Drive (split.py)
    if not lv:
        return 0
    lvis = {u for uids in json.loads(gzip.decompress(lv.content)).values() for u in uids}
    shards = {}
    for uid, p in paths.items():
        shards.setdefault(p.split("/")[1], []).append((uid, p))
    order = sorted(shards)
    if lane == "sketchfab_mid":
        order = order[len(order) // 2:]
    elif lane == "sketchfab_rev":
        order = order[::-1]
    n = 0
    while pos["shard"] < len(order) and st.get("added", 0) < QUOTA[lane] and not sink.full():
        shard = order[pos["shard"]]
        m = get(s, f"{OBJA}/metadata/{shard}.json.gz")
        meta = json.loads(gzip.decompress(m.content)) if m else {}
        objs = sorted(shards[shard])
        while pos["i"] < len(objs) and st.get("added", 0) < QUOTA[lane] and not sink.full():
            items = []
            for uid, p in objs[pos["i"]:pos["i"] + 48]:  # 48 at a time, fetched 12 in parallel
                md = meta.get(uid) or {}
                if split.objaverse_owner(uid, md, lvis) != "assets":
                    continue  # another Drive's object (vehicles: mobility; LVIS / buildings: Lintel)
                cats = md.get("categories") or []
                cat = safe(cats[0].get("name") if cats and isinstance(cats[0], dict) else "Uncategorised", 50)
                name = safe(md.get("name") or uid, 70)
                items.append((f"{OBJA}/{p}", CAP, f"{MODELS}/GLB/Sketchfab/{cat}/{name} {uid[:8]}.glb",
                              lambda h: h[:4] == b"glTF"))
            pos["i"] += min(48, len(objs) - pos["i"])
            got = len(fetch_many(sink, items))
            n += got
            st["added"] = st.get("added", 0) + got
        if pos["i"] >= len(objs):
            pos["shard"], pos["i"] = pos["shard"] + 1, 0
    return n


GH_TYPES = ["fbx", "obj", "blend", "stl", "3ds", "dae", "gltf", "glb", "ply"]


def github_models(sink, st, cache="cache/github.parquet"):
    """Model files in public GitHub repositories (Objaverse-XL GitHub index, millions of files), taken
    round-robin across formats so every format keeps growing."""
    import pyarrow.compute as pc
    s = gh()
    t = _parquet(session(), f"{XL}/github/github.parquet", cache, ["fileIdentifier", "fileType"],
                 [("fileType", "in", GH_TYPES)])
    by_type = {}
    for ft in GH_TYPES:
        col = t.filter(pc.equal(t["fileType"], ft))["fileIdentifier"]
        by_type[ft] = col
    pos = st.setdefault("ghm", {})
    n = 0
    live = [ft for ft in GH_TYPES if len(by_type[ft])]
    while live and st.get("added", 0) < QUOTA["github_models"] and not sink.full():
        for ft in list(live):
            i = pos.get(ft, 0)
            if i >= len(by_type[ft]):
                live.remove(ft)
                continue
            pos[ft] = i + 1
            url = by_type[ft][i].as_py()
            # https://github.com/<owner>/<repo>/blob/<sha>/<path>
            try:
                _, rest = url.split("github.com/", 1)
                owner, repo, _, sha, path = rest.split("/", 4)
            except ValueError:
                continue
            if split.repo_owner(f"{owner}/{repo}") != "assets":
                continue  # the Lintel Drive's repository (split.py)
            fname = path.rsplit("/", 1)[-1]
            base = f"{MODELS}/{FOLDER[ft]}/GitHub/{safe(repo, 60)} {sha[:6]}"
            if gh_file(s, sink, f"{owner}/{repo}", sha, quote(path), f"{base}/{safe(fname, 100)}", CAP):
                n += 1
                st["added"] = st.get("added", 0) + 1
                for side in SIDECAR.get(ft, []):
                    sp = path.rsplit(".", 1)[0] + "." + side
                    gh_file(s, sink, f"{owner}/{repo}", sha, quote(sp),
                            f"{base}/{safe(sp.rsplit('/', 1)[-1], 100)}", 20 * 2 ** 20)
    return n


def thingi10k(sink, st):
    """Thingi10K: 10,000 3D-printing meshes from Thingiverse (research dataset), streamed from its archive.
    A dropped connection resumes from the last saved member (up to 5 tries a run)."""
    n = 0
    for _ in range(5):
        if st.get("t10k_done") or sink.full():
            break
        try:
            n += _thingi10k(sink, st)
        except Exception as exc:
            print(f"thingi10k: stream dropped ({type(exc).__name__}), resuming")
    return n


def _thingi10k(sink, st):
    s = session()
    skip = st.get("t10k_i", 0)
    n = i = 0
    with s.get(f"{HF}/Thingi10K/Thingi10K/resolve/main/Thingi10K.tar.gz", stream=True, timeout=600) as r:
        if r.status_code != 200:
            return 0
        with tarfile.open(fileobj=r.raw, mode="r|gz") as tf:
            for m in tf:
                if not m.isfile():
                    continue
                i += 1
                if i <= skip:
                    continue
                if sink.full():
                    return n
                e = m.name.rsplit(".", 1)[-1].lower()
                if e in FOLDER:
                    data = tf.extractfile(m).read()
                    sink.write_bytes(f"{MODELS}/{FOLDER[e]}/Thingi10K/{safe(m.name.rsplit('/', 1)[-1], 100)}", data)
                    n += 1
                st["t10k_i"] = i
    st["t10k_done"] = True
    return n


def smithsonian(sink, st):
    """Smithsonian 3D digitisations (CC0), .glb, named by object title."""
    s = session()
    t = _parquet(s, f"{XL}/smithsonian/smithsonian.parquet", "cache/smithsonian.parquet",
                 ["fileIdentifier", "metadata"]).to_pylist()
    i = st.get("smith_i", 0)
    n = 0
    while i < len(t) and not sink.full():
        row = t[i]
        i += 1
        title = (json.loads(row["metadata"] or "{}").get("title") or row["fileIdentifier"].rsplit("/", 1)[-1])
        if download(s, row["fileIdentifier"], CAP * 2, sink,
                    f"{MODELS}/GLB/Smithsonian/{safe(title, 90)} {i}.glb", lambda h: h[:4] == b"glTF"):
            n += 1
    st["smith_i"] = i
    return n


def polyhaven(sink, st, res="2k"):
    """Poly Haven models: .blend, .fbx and .gltf with their textures, one folder per model."""
    s = session()
    r = get(s, "https://api.polyhaven.com/assets", params={"t": "models"})
    assets = r.json() if r else {}
    done = set(st.setdefault("ph_done", []))
    n = 0
    for aid, info in sorted(assets.items()):
        if aid in done or sink.full():
            continue
        fr = get(s, f"https://api.polyhaven.com/files/{aid}")
        files = fr.json() if fr else {}
        name = safe(info.get("name") or aid, 80)
        for fmt, folder in (("blend", "BLEND"), ("fbx", "FBX"), ("gltf", "GLTF")):
            entry = ((files.get(fmt) or {}).get(res) or (files.get(fmt) or {}).get("1k") or {}).get(fmt) or {}
            if not entry.get("url"):
                continue
            dest = f"{MODELS}/{folder}/Poly Haven/{name}"
            if download(s, entry["url"], 500 * 2 ** 20, sink, f"{dest}/{entry['url'].rsplit('/', 1)[-1]}"):
                n += 1
            for inc_path, inc in (entry.get("include") or {}).items():
                download(s, inc["url"], 200 * 2 ** 20, sink, f"{dest}/{inc_path}")
        st["ph_done"].append(aid)
    return n


CURATED = {  # repository: collection name
    "KhronosGroup/glTF-Sample-Assets": "Khronos glTF samples",
    "nasa/NASA-3D-Resources": "NASA",
    "alecjacobson/common-3d-test-models": "Common test models",
    "mikedh/trimesh": "trimesh test models",
    "assimp/assimp": "Assimp test models",
    "mrdoob/three.js": "three.js examples",
    "BabylonJS/Assets": "Babylon.js assets",
    "godotengine/godot-demo-projects": "Godot demos",
}


def curated(sink, st):
    """Every model file in curated sample-asset repositories (all formats)."""
    s = gh()
    done = st.setdefault("cur", {})
    n = 0
    for repo, coll in CURATED.items():
        if sink.full():
            break
        r = get(s, f"https://api.github.com/repos/{repo}")
        if not r or done.get(repo) == r.json().get("pushed_at"):
            continue
        branch = r.json()["default_branch"]
        files = [f for f in gh_tree(s, repo, branch) if f["path"].rsplit(".", 1)[-1].lower() in FOLDER
                 and f.get("size", 0) <= CAP]
        start = done.get(repo + "#i", 0)
        for i, f in enumerate(files[start:], start):
            if sink.full():
                done[repo + "#i"] = i
                return n
            e = f["path"].rsplit(".", 1)[-1].lower()
            if gh_file(s, sink, repo, branch, quote(f["path"]), f"{MODELS}/{FOLDER[e]}/{coll}/{f['path']}", CAP):
                n += 1
        done[repo] = r.json().get("pushed_at")
        done.pop(repo + "#i", None)
    return n


def thingiverse(sink, st, cache="cache/thingiverse.parquet"):
    """Thingiverse STL files through the official API (needs THINGIVERSE_TOKEN): the Objaverse-XL index lists
    3.7 million files; the API is called no faster than its rate limit allows."""
    token = os.environ.get("THINGIVERSE_TOKEN")
    if not token:
        return 0
    s = session()
    s.headers["Authorization"] = f"Bearer {token}"
    t = _parquet(session(), f"{XL}/thingiverse/thingiverse.parquet", cache, ["fileIdentifier", "metadata"])
    ids, meta = t["fileIdentifier"], t["metadata"]
    i = st.get("tv_i", 0)
    n = 0
    while i < len(ids) and not sink.full():
        url = ids[i].as_py()  # https://thingiverse.com/thing:<thing>/files?fileId=<file>
        md = json.loads(meta[i].as_py() or "{}")
        i += 1
        try:
            thing = url.split("thing:", 1)[1].split("/", 1)[0]
            fid = url.rsplit("fileId=", 1)[1]
        except IndexError:
            continue
        for _ in range(5):
            r = s.get(f"https://api.thingiverse.com/files/{fid}/download", timeout=120, allow_redirects=False)
            if r.status_code != 429:
                break
            time.sleep(60)
        loc = r.headers.get("Location") if r.status_code in (301, 302, 303, 307) else None
        if not loc:
            continue
        fname = safe(md.get("filename") or f"{fid}.stl", 100)
        if download(session(), loc, CAP, sink, f"{MODELS}/STL/Thingiverse/{thing}/{fname}", not_html):
            n += 1
        time.sleep(0.9)  # ~300 calls per 5 minutes
    st["tv_i"] = i
    return n


SOURCES = {"sketchfab": sketchfab, "sketchfab_mid": lambda sink, st: sketchfab(sink, st, "sketchfab_mid"),
           "sketchfab_rev": lambda sink, st: sketchfab(sink, st, "sketchfab_rev"), "github_models": github_models, "thingi10k": thingi10k,
           "smithsonian": smithsonian, "polyhaven": polyhaven, "curated": curated, "thingiverse": thingiverse}
