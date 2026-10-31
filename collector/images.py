"""Images (.jpg .jpeg .png .tiff), about 250 GB in all: Wikimedia Commons quality images, NASA image library,
The Met and the Art Institute of Chicago open-access collections. Filed by format, then collection."""
import time

from .common import get, safe, session
from .util import IMAGES, download

LIMIT = 250 * 2 ** 30
CAP = 40 * 2 ** 20
IMG_MAGIC = (b"\xff\xd8\xff", b"\x89PNG", b"II*\x00", b"MM\x00*")


def _is_img(head):
    return head.startswith(IMG_MAGIC)


def _fmt(url):
    e = url.split("?", 1)[0].rsplit(".", 1)[-1].lower()
    return {"jpg": "JPG", "jpeg": "JPEG", "png": "PNG", "tif": "TIFF", "tiff": "TIFF"}.get(e)


def _save(s, sink, st, url, coll, title):
    fmt = _fmt(url)
    if st["img_bytes"] >= st.get("img_cap", LIMIT):
        sink.slice_end = 0  # image share used up: end this collection's slice
        return 0
    if not fmt:
        return 0
    e = url.split("?", 1)[0].rsplit(".", 1)[-1].lower()
    n = download(s, url, CAP, sink, f"{IMAGES}/{fmt}/{coll}/{safe(title, 110)}.{e}", _is_img)
    st["img_bytes"] += n
    return 1 if n else 0


COMMONS = ["Category:Quality images", "Category:Featured pictures on Wikimedia Commons", "Category:Valued images"]


def commons(sink, st):
    s = session()
    n = 0
    for cat in COMMONS:
        key = "cm:" + cat
        cont = st.get(key, "")
        if cont == "done":
            continue
        while not sink.full():
            params = {"action": "query", "format": "json", "generator": "categorymembers", "gcmtitle": cat,
                      "gcmtype": "file", "gcmlimit": 50, "prop": "imageinfo", "iiprop": "url|size|mime",
                      "iiurlwidth": 3000}
            if cont:
                params["gcmcontinue"] = cont
            r = get(s, "https://commons.wikimedia.org/w/api.php", params=params)
            if not r:
                break
            d = r.json()
            for page in (d.get("query") or {}).get("pages", {}).values():
                info = (page.get("imageinfo") or [{}])[0]
                url = info.get("url") or ""
                if info.get("size", 0) > CAP and info.get("thumburl"):
                    url = info["thumburl"]
                title = page.get("title", "").replace("File:", "").rsplit(".", 1)[0]
                n += _save(s, sink, st, url, "Wikimedia Commons", title)
            cont = (d.get("continue") or {}).get("gcmcontinue")
            st[key] = cont or "done"
            if not cont:
                break
        if sink.full():
            break
    return n


NASA_Q = ["galaxy", "nebula", "earth", "mars", "moon", "jupiter", "saturn", "sun", "astronaut", "space station",
          "rocket launch", "hubble", "webb", "aurora", "hurricane", "aircraft", "satellite", "comet", "eclipse",
          "spacewalk", "apollo", "shuttle", "rover", "telescope", "clouds", "ocean", "volcano", "desert"]


def nasa(sink, st):
    s = session()
    pos = st.setdefault("nasa", {})
    n = 0
    for q in NASA_Q:
        page = pos.get(q, 1)
        while page and page <= 100 and not sink.full():
            r = get(s, "https://images-api.nasa.gov/search", params={"q": q, "media_type": "image", "page": page})
            items = ((r.json().get("collection") or {}).get("items") or []) if r else []
            for it in items:
                if sink.full():
                    break
                d = (it.get("data") or [{}])[0]
                a = get(s, f"https://images-api.nasa.gov/asset/{d.get('nasa_id')}")
                hrefs = [x["href"] for x in ((a.json().get("collection") or {}).get("items") or [])] if a else []
                pick = next((h for h in hrefs if "~orig." in h), None) or next((h for h in hrefs if "~large." in h), None)
                if pick:
                    n += _save(s, sink, st, pick.replace("http://", "https://"), "NASA",
                               d.get("title") or d.get("nasa_id"))
            page = page + 1 if items else 0
            pos[q] = page
        if sink.full():
            break
    return n


def met(sink, st):
    s = session()
    if "met_ids" not in st:
        r = get(s, "https://collectionapi.metmuseum.org/public/collection/v1/search",
                params={"hasImages": "true", "q": "*"})
        st["met_ids"] = (r.json().get("objectIDs") or []) if r else []
        st["met_i"] = 0
    ids = st["met_ids"]
    n = 0
    while st["met_i"] < len(ids) and not sink.full():
        oid = ids[st["met_i"]]
        st["met_i"] += 1
        r = get(s, f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}", tries=2)
        o = r.json() if r else {}
        if o.get("isPublicDomain") and o.get("primaryImage"):
            dept = safe(o.get("department") or "Collection", 40)
            n += _save(s, sink, st, o["primaryImage"], f"The Met/{dept}", f"{o.get('title') or oid} {oid}")
        time.sleep(0.02)
    return n


def artic(sink, st):
    s = session()
    page = st.get("aic_page", 1)
    n = 0
    while page and not sink.full():
        r = get(s, "https://api.artic.edu/api/v1/artworks/search", params={
            "query[term][is_public_domain]": "true", "fields": "id,title,image_id,department_title",
            "limit": 100, "page": page})
        data = (r.json().get("data") or []) if r else []
        for a in data:
            if a.get("image_id") and not sink.full():
                n += _save(s, sink, st, f"https://www.artic.edu/iiif/2/{a['image_id']}/full/1686,/0/default.jpg",
                           f"Art Institute of Chicago/{safe(a.get('department_title') or 'Collection', 40)}",
                           f"{a.get('title') or a['id']} {a['id']}")
        page = page + 1 if data and page < 100 else 0  # search pages stop at 10,000 results
        st["aic_page"] = page
    return n


PARTS = [commons, nasa, met, artic]


def images(sink, st):
    """General collections: 30% of the image space (buildings and cars, in focus.py, take the other 70%);
    the time slice is shared between the four collections so all of them grow."""
    st.setdefault("img_bytes", 0)
    st["img_cap"] = int(LIMIT * 0.3)
    end = sink.slice_end
    n = 0
    for i, part in enumerate(PARTS):
        if st["img_bytes"] >= st["img_cap"]:
            break
        sink.slice_end = time.time() + max(60, (end - time.time()) / (len(PARTS) - i))
        n += part(sink, st)
        sink.slice_end = end
    return n


SOURCES = {"images": images}
