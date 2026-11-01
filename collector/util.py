"""Download helpers shared by every source."""
import os
import time

from .common import get, session

LIB = "Asset Library"
MODELS = "01 3D Models"
CAD = "02 CAD Drawings"
IMAGES = "03 Images"
SHEETS = "04 Spreadsheets"
BREX = "05 Brex"
ZOOM = "06 Zoom Calls"


def ext(path):
    name = path.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def download(s, url, cap, sink, rel, magic=None, timeout=180):
    """Stream url to the sink path; drop it if it is empty, bigger than cap or (with magic) not that file type.
    Returns the size saved, or 0."""
    p = sink.path(rel)
    try:
        with s.get(url, stream=True, timeout=timeout) as r:
            if r.status_code != 200 or int(r.headers.get("Content-Length") or 0) > cap:
                return 0
            n = 0
            with open(p, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    n += len(chunk)
                    if n > cap:
                        break
                    f.write(chunk)
        bad = n > cap or n == 0
        if not bad and magic:
            with open(p, "rb") as f:
                bad = not magic(f.read(512))
        if bad:
            os.remove(p)
            return 0
        sink.wrote(p)
        return n
    except Exception:
        if os.path.exists(p):
            os.remove(p)
        return 0


def not_html(head):
    """Rejects error and landing pages served in place of a file."""
    h = head.lstrip()[:15].lower()
    return not (h.startswith(b"<!doctype") or h.startswith(b"<html") or h.startswith(b"<?xml version") and
                b"<html" in head.lower())


def gh():
    s = session()
    if os.environ.get("GITHUB_TOKEN"):
        s.headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    s.headers["Accept"] = "application/vnd.github+json"
    return s


def gh_search(s, q, page):
    time.sleep(2.2)  # search API: 30 requests a minute
    r = get(s, "https://api.github.com/search/repositories",
            params={"q": q, "sort": "stars", "order": "desc", "per_page": 30, "page": page})
    return r.json().get("items", []) if r else []


def gh_tree(s, repo, branch):
    r = get(s, f"https://api.github.com/repos/{repo}/git/trees/{branch}", params={"recursive": "1"})
    return [f for f in (r.json().get("tree", []) if r else []) if f.get("type") == "blob"]


LFS_PTR = b"version https://git-lfs"


def gh_file(s, sink, repo, ref, path, rel, cap):
    """One file from a GitHub repository; Git LFS pointers are replaced by the real content. The pointer is
    spotted before the file is handed to the sink (a hand-over can ship it to Drive at once)."""
    lfs = []

    def check(head):
        if head.startswith(LFS_PTR):
            lfs.append(1)
            return False
        return not_html(head)

    n = download(s, f"https://raw.githubusercontent.com/{repo}/{ref}/{path}", cap, sink, rel, check)
    if lfs:
        n = download(s, f"https://media.githubusercontent.com/media/{repo}/{ref}/{path}", cap, sink, rel, not_html)
    return n
