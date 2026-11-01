"""Building and car images, real photos and illustrated / animated / 3D-rendered ones: Wikimedia Commons search
and Openverse (no key), plus Unsplash, Pexels and Pixabay when their API keys are set (UNSPLASH_ACCESS_KEY,
PEXELS_API_KEY, PIXABAY_API_KEY). Filed as 03 Images/<Buildings & Architecture | Cars>/<Photos | Illustrations
& Renders>/<topic>/."""
import os
import time

from .common import get, safe, session
from .images import CAP, _is_img
from .util import IMAGES, download

THEMES = {
    "Buildings & Architecture": {
        "Photos": ["house", "skyscraper", "modern architecture", "modern house exterior", "villa", "apartment building",
                   "office building", "glass facade", "brutalist architecture", "art deco building", "gothic cathedral",
                   "mosque architecture", "temple architecture", "castle", "bridge architecture", "stadium", "museum building",
                   "train station architecture", "airport terminal", "interior design living room", "kitchen interior",
                   "staircase architecture", "atrium", "timber house", "tiny house", "farmhouse", "townhouse",
                   "city skyline", "street facade", "building construction site", "concrete architecture",
                   "minimalist architecture", "futuristic building", "historic building", "lighthouse", "pagoda"],
        "Illustrations & Renders": ["architectural rendering", "architecture 3d render", "building illustration",
                                    "isometric building", "house illustration", "city illustration", "cartoon house",
                                    "cartoon city", "low poly building", "pixel art building", "architecture sketch",
                                    "floor plan illustration", "building blueprint", "fantasy castle illustration",
                                    "futuristic city concept art"],
    },
    "Cars": {
        "Photos": ["sports car", "supercar", "classic car", "vintage car", "muscle car", "electric car", "sedan car",
                   "SUV car", "pickup truck", "hatchback car", "convertible car", "race car", "rally car", "Formula 1 car",
                   "car interior", "car dashboard", "car engine", "car wheel", "concept car", "police car", "taxi car",
                   "Ferrari", "Lamborghini", "Porsche", "BMW car", "Mercedes-Benz car", "Audi car", "Toyota car",
                   "Ford Mustang", "Chevrolet Corvette", "Tesla car", "Volkswagen Beetle", "Mini Cooper", "Jeep",
                   "Land Rover", "Nissan GT-R", "Honda car", "Mazda MX-5", "car show", "parked cars street"],
        "Illustrations & Renders": ["car illustration", "car 3d render", "car rendering", "cartoon car",
                                    "car vector", "car drawing", "car sketch", "concept car sketch", "low poly car",
                                    "pixel art car", "race car illustration", "retro car poster", "isometric car",
                                    "car blueprint", "anime car"],
    },
}


def _queries():
    for theme, kinds in THEMES.items():
        for kind, qs in kinds.items():
            for q in qs:
                yield theme, kind, q


def _save(s, sink, st, url, theme, kind, q, source, title, e):
    if st["focus_bytes"] >= st["focus_cap"]:
        sink.slice_end = 0
        return 0
    n = download(s, url, CAP, sink, f"{IMAGES}/{theme}/{kind}/{safe(q.title(), 50)}/{source}/{safe(title, 100)}.{e}",
                 _is_img)
    st["focus_bytes"] += n
    return 1 if n else 0


def _ext(url, default="jpg"):
    e = url.split("?", 1)[0].rsplit(".", 1)[-1].lower()
    return e if e in ("jpg", "jpeg", "png", "tif", "tiff") else default


def commons(sink, st):
    s = session()
    pos = st.setdefault("fc_commons", {})
    n = 0
    for theme, kind, q in _queries():
        off = pos.get(q, 0)
        search = f"filetype:{'bitmap' if kind == 'Photos' else 'bitmap|drawing'} {q}"
        while off is not None and off < 9950 and not sink.full():
            r = get(s, "https://commons.wikimedia.org/w/api.php", params={
                "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrsearch": search,
                "gsrlimit": 50, "gsroffset": off, "prop": "imageinfo", "iiprop": "url|size|mime", "iiurlwidth": 2560})
            d = r.json() if r else {}
            pages = (d.get("query") or {}).get("pages", {})
            for p in pages.values():
                info = (p.get("imageinfo") or [{}])[0]
                url = info.get("url") or ""
                if info.get("mime") == "image/svg+xml" or info.get("size", 0) > CAP:
                    url = info.get("thumburl") or ""  # drawings and very large files: 2560 px rendering
                if url:
                    title = p.get("title", "").replace("File:", "").rsplit(".", 1)[0]
                    n += _save(s, sink, st, url, theme, kind, q, "Wikimedia Commons", title, _ext(url, "png"))
            off = (d.get("continue") or {}).get("gsroffset") if pages else None
            pos[q] = off if off is not None else 10000
        if sink.full():
            break
    return n


def openverse(sink, st):
    s = session()
    pos = st.setdefault("fc_openverse", {})
    n = 0
    for theme, kind, q in _queries():
        page = pos.get(q, 1)
        while page and page <= 20 and not sink.full():
            r = get(s, "https://api.openverse.org/v1/images/", tries=3, params={
                "q": q, "page": page, "page_size": 20, "category": "photograph" if kind == "Photos" else
                "illustration,digitized_artwork"})
            res = (r.json().get("results") or []) if r else []
            for it in res:
                if it.get("url"):
                    n += _save(s, sink, st, it["url"], theme, kind, q, "Openverse",
                               f"{it.get('title') or it['id']} {it['id'][:8]}", _ext(it["url"]))
            page = page + 1 if res else 0
            pos[q] = page
            time.sleep(1.5)  # anonymous rate limit
        if sink.full():
            break
    return n


def unsplash(sink, st):
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key:
        return 0
    s = session()
    s.headers["Authorization"] = f"Client-ID {key}"
    pos = st.setdefault("fc_unsplash", {})
    n = 0
    for theme, kind, q in _queries():
        page = pos.get(q, 1)
        while page and page <= 30 and not sink.full():
            r = s.get("https://api.unsplash.com/search/photos", params={"query": q, "page": page, "per_page": 30},
                      timeout=60)
            if r.status_code == 403:  # hourly limit: wait for the next hour
                time.sleep(300)
                continue
            res = r.json().get("results", []) if r.status_code == 200 else []
            for p in res:
                dl = get(s, p["links"]["download_location"])  # required by the API guidelines
                url = (dl.json().get("url") if dl else None) or p["urls"]["full"]
                n += _save(session(), sink, st, url, theme, kind, q, "Unsplash",
                           f"{p.get('alt_description') or p['id']} {p['id']}", "jpg")
            page = page + 1 if res else 0
            pos[q] = page
        if sink.full():
            break
    return n


def pexels(sink, st):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return 0
    s = session()
    s.headers["Authorization"] = key
    pos = st.setdefault("fc_pexels", {})
    n = 0
    for theme, kind, q in _queries():
        page = pos.get(q, 1)
        while page and page <= 40 and not sink.full():
            r = s.get("https://api.pexels.com/v1/search", params={"query": q, "page": page, "per_page": 80}, timeout=60)
            if r.status_code == 429:
                time.sleep(600)
                continue
            res = r.json().get("photos", []) if r.status_code == 200 else []
            for p in res:
                url = p["src"].get("original") or p["src"]["large2x"]
                n += _save(session(), sink, st, url, theme, kind, q, "Pexels",
                           f"{p.get('alt') or p['id']} {p['id']}", _ext(url))
            page = page + 1 if res else 0
            pos[q] = page
            time.sleep(18)  # 200 requests an hour
        if sink.full():
            break
    return n


def pixabay(sink, st):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return 0
    s = session()
    pos = st.setdefault("fc_pixabay", {})
    n = 0
    for theme, kind, q in _queries():
        page = pos.get(q, 1)
        while page and page <= 3 and not sink.full():  # the API returns at most 500 results per search
            r = get(s, "https://pixabay.com/api/", params={
                "key": key, "q": q, "page": page, "per_page": 200, "safesearch": "true",
                "image_type": "photo" if kind == "Photos" else "illustration"})
            res = (r.json().get("hits") or []) if r else []
            for h in res:
                url = h.get("largeImageURL")
                if url:
                    n += _save(s, sink, st, url, theme, kind, q, "Pixabay", f"{h.get('tags') or h['id']} {h['id']}",
                               _ext(url))
            page = page + 1 if res else 0
            pos[q] = page
            time.sleep(1)
        if sink.full():
            break
    return n


PARTS = [commons, unsplash, pexels, pixabay, openverse]


def focus(sink, st):
    """Buildings and cars: up to 70% of the image space, time shared between the sources that are available."""
    from .images import LIMIT
    st.setdefault("focus_bytes", 0)
    st["focus_cap"] = int(LIMIT * 0.7)
    parts = [p for p in PARTS if p.__name__ in ("commons", "openverse") or os.environ.get(
        {"unsplash": "UNSPLASH_ACCESS_KEY", "pexels": "PEXELS_API_KEY", "pixabay": "PIXABAY_API_KEY"}[p.__name__])]
    end = sink.slice_end
    n = 0
    for i, part in enumerate(parts):
        if st["focus_bytes"] >= st["focus_cap"]:
            break
        sink.slice_end = time.time() + max(60, (end - time.time()) / (len(parts) - i))
        try:
            n += part(sink, st)
        except Exception as exc:  # one source failing must not stop the others
            print(f"focus/{part.__name__}: {type(exc).__name__}")
        sink.slice_end = end
    return n


SOURCES = {"focus": focus}
