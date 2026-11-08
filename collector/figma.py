"""Modified Figma files (user, 2026-11-07: "add 130 modified figma files"): real Figma design files (.fig) from public
GitHub repositories, each turned into a new colour variant: every colour on the canvas has its hue turned by an
angle of its own (layout, text and images stay as drawn), the preview thumbnail is re-coloured to match and the
file's name in meta.json is the new one. Filed as 09 Figma Files/<repository>/<file>.fig. Stops at 130 files; at
most 3 from one repository."""
import colorsys
import io
import json
import os
import re
import subprocess
import tempfile
import zipfile
from urllib.parse import quote

from .common import safe
from .util import LFS_PTR, gh, gh_search, gh_tree

FIGMA = "09 Figma Files"
LIMIT, PER_REPO = 130, 3
CAP = 150 * 2 ** 20
QUERIES = ["topic:figma", "topic:figma-design", "topic:figma-file", "topic:ui-kit figma", "topic:design-system figma",
           "figma in:readme language:HTML", "figma in:readme language:CSS", "figma in:readme language:JavaScript",
           "figma in:readme language:TypeScript", "figma in:readme language:Dart", "figma in:readme language:Swift",
           "figma in:readme language:Kotlin", "\"fig file\" in:readme", "\"design.fig\"", "figma design file",
           "figma mockup", "figma landing page", "figma ui kit", "figma dashboard", "figma app design",
           "figma website design", "figma portfolio", "figma template", "figma wireframe", "figma prototype"]
FIXTURE = re.compile(r"(^|/)(tests?|fixtures?|__tests__|spec|examples?/parser|node_modules)/", re.I)
JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figmod.js")


def _real(data):
    if len(data) < 2048:
        return False
    if data[:8] == b"fig-kiwi":
        return True
    if data[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                return "canvas.fig" in z.namelist()
        except zipfile.BadZipFile:
            return False
    return False


def _canvas(data, seed):
    with tempfile.TemporaryDirectory() as t:
        a, b = os.path.join(t, "in.fig"), os.path.join(t, "out.fig")
        open(a, "wb").write(data)
        r = subprocess.run(["node", JS, a, b, seed], capture_output=True, timeout=600)
        if r.returncode != 0 or not os.path.exists(b) or int((r.stdout or b"0").strip() or 0) == 0:
            return None  # nothing re-coloured (a grey design) or a canvas the decoder cannot read
        return open(b, "rb").read()


def _thumb(png, seed):
    from PIL import Image
    turn = (40 + sum(map(ord, seed)) % 280) / 360
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            if s > 0.02:
                r, g, b = (round(v * 255) for v in colorsys.hls_to_rgb((h + turn) % 1, l, s))
            px[x, y] = (r, g, b, a)
    out = io.BytesIO()
    im.save(out, "PNG")
    return out.getvalue()


def modify(data, seed, title):
    """The variant of one .fig file, or None."""
    if data[:8] == b"fig-kiwi":
        return _canvas(data, seed)
    src = zipfile.ZipFile(io.BytesIO(data))
    canvas = _canvas(src.read("canvas.fig"), seed)
    if not canvas:
        return None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            raw = src.read(info)
            if info.filename == "canvas.fig":
                raw = canvas
            elif info.filename == "thumbnail.png":
                try:
                    raw = _thumb(raw, seed)
                except Exception:  # noqa: BLE001
                    pass
            elif info.filename == "meta.json":
                try:
                    meta = json.loads(raw)
                    meta["file_name"] = title
                    raw = json.dumps(meta).encode()
                except ValueError:
                    pass
            dst.writestr(info.filename, raw, zipfile.ZIP_STORED if info.filename == "canvas.fig" else zipfile.ZIP_DEFLATED)
    return buf.getvalue()


def figma(sink, st):
    s = gh()
    done = st.setdefault("figma_repos", [])
    pages = st.setdefault("figma_page", {})
    if sink.live:  # count what is really on the Drive (two same-named files had overwritten each other: 129, not 130)
        import subprocess
        r = subprocess.run(["rclone", "lsf", "-R", "--files-only", f"{sink.remote}/{FIGMA}", "-q"],
                           capture_output=True, text=True, timeout=900)
        if r.returncode == 0:
            st["figma_count"] = sum(1 for x in r.stdout.splitlines() if x.lower().endswith(".fig"))
    count = lambda: st.get("figma_count", 0)  # noqa: E731
    n = 0
    for q in QUERIES:
        page = pages.get(q, 1)
        while page <= 10 and count() < LIMIT and not sink.full():
            items = gh_search(s, f"{q} fork:false", page)
            page = pages[q] = page + 1 if items else 11
            for item in items:
                name, ref = item["full_name"], item["default_branch"]
                if name in done or count() >= LIMIT or sink.full():
                    continue
                done.append(name)
                figs = [f["path"] for f in gh_tree(s, name, ref) if f["path"].lower().endswith(".fig")
                        and 2048 <= f.get("size", 0) <= CAP and not FIXTURE.search(f["path"])]
                took = 0
                for path in figs:
                    if took >= PER_REPO or count() >= LIMIT:
                        break
                    r = s.get(f"https://raw.githubusercontent.com/{name}/{ref}/{quote(path)}", timeout=180)
                    data = r.content if r.ok else b""
                    if data.startswith(LFS_PTR):
                        r = s.get(f"https://media.githubusercontent.com/media/{name}/{ref}/{quote(path)}", timeout=300)
                        data = r.content if r.ok else b""
                    if not _real(data):  # MATLAB figures and other .fig files are not Figma designs
                        continue
                    title = safe(path.rsplit("/", 1)[-1][:-4], 80)
                    try:
                        new = modify(data, f"{name}/{path}", title)
                    except Exception:  # noqa: BLE001
                        new = None
                    if not new:
                        continue
                    tag = __import__("hashlib").md5(f"{name}/{path}".encode()).hexdigest()[:6]
                    sink.write_bytes(f"{FIGMA}/{safe(item['name'], 60)}/{title} {tag}.fig", new)
                    st["figma_count"] = count() + 1
                    took += 1
                    n += 1
    return n


SOURCES = {"figma": figma}
