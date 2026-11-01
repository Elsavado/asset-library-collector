"""Adobe creative files (user, 2026-11-01: "adobe creative files like 320 of them"): Photoshop, Illustrator,
InDesign, After Effects, Premiere Pro and XD source files from GitHub repositories for design topics, filed as
07 Adobe Creative Files/<app>/<repository>/<path>. Stops at 320 files; no single app takes more than 120 and no
repository more than 15, so the set stays mixed."""
from urllib.parse import quote

from .common import safe
from .util import gh, gh_file, gh_search, gh_tree

ADOBE = "07 Adobe Creative Files"
LIMIT, PER_APP, PER_REPO = 320, 120, 15
APP = {"psd": "Photoshop (PSD)", "psb": "Photoshop (PSD)", "ai": "Illustrator (AI)", "indd": "InDesign (INDD, IDML)",
       "idml": "InDesign (INDD, IDML)", "indt": "InDesign (INDD, IDML)", "aep": "After Effects (AEP)",
       "aet": "After Effects (AEP)", "prproj": "Premiere Pro (PRPROJ)", "xd": "Adobe XD", "abr": "Photoshop Brushes (ABR)"}
CAP = 150 * 2 ** 20
TOPICS = ["psd", "photoshop", "psd-template", "psd-templates", "psd-files", "mockup", "mockups", "adobe-illustrator",
          "illustrator", "ai-files", "vector-graphics", "indesign", "idml", "after-effects", "aftereffects",
          "after-effects-template", "premiere-pro", "adobe-xd", "xd", "ui-kit", "design-resources", "design-assets",
          "logo-design", "branding", "graphic-design", "photoshop-brushes", "adobe"]


def _ext(p):
    n = p.rsplit("/", 1)[-1]
    return n.rsplit(".", 1)[-1].lower() if "." in n else ""


def adobe(sink, st):
    s = gh()
    count = st.setdefault("adobe_count", {})
    done = st.setdefault("adobe_repos", [])
    pages = st.setdefault("adobe_page", {})
    total = lambda: sum(count.values())  # noqa: E731
    n = 0
    for t in TOPICS:
        page = pages.get(t, 1)
        while page <= 10 and total() < LIMIT and not sink.full():
            items = gh_search(s, f"topic:{t} archived:false fork:false", page)
            page = pages[t] = page + 1 if items else 11
            for item in items:
                name = item["full_name"]
                if name in done or total() >= LIMIT or sink.full():
                    continue
                files = [f for f in gh_tree(s, name, item["default_branch"])
                         if _ext(f["path"]) in APP and 1024 < f.get("size", 0) <= CAP]
                took = 0
                for f in files:
                    app = APP[_ext(f["path"])]
                    if took >= PER_REPO or total() >= LIMIT or sink.full():
                        break
                    if count.get(app, 0) >= PER_APP:
                        continue
                    if gh_file(s, sink, name, item["default_branch"], quote(f["path"]),
                               f"{ADOBE}/{app}/{safe(item['name'], 60)}/{f['path']}", CAP):
                        count[app] = count.get(app, 0) + 1
                        took += 1
                        n += 1
                if not sink.full():
                    done.append(name)
        if total() >= LIMIT or sink.full():
            break
    print(f"adobe: {total()} of {LIMIT} files so far ({', '.join(f'{k} {v}' for k, v in sorted(count.items()))})")
    return n


SOURCES = {"adobe": adobe}
