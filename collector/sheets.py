"""3,100 spreadsheets (.xlsx .xls .csv) from English-language government open-data catalogues (UK, Canada,
Australia, Ireland, UN OCHA HDX): about 1,200 XLSX, 600 XLS and 1,200 CSV, filed by format, then publishing
organisation."""
from .common import english, get, safe, session
from .util import SHEETS, download, not_html

TARGET = {"xlsx": 1250, "xls": 600, "csv": 1250}
TOTAL = 3100  # user 2026-11-07: "make sure spreadsheets reach 3100" (files on the Drive, not downloads)
CAP = 100 * 2 ** 20
MAGIC = {"xlsx": lambda h: h[:2] == b"PK", "xls": lambda h: h[:4] == b"\xd0\xcf\x11\xe0",
         "csv": lambda h: not_html(h) and b"," in h}
CATALOGS = [("https://ckan.publishing.service.gov.uk/api/action/package_search", "UK"),
            ("https://open.canada.ca/data/api/action/package_search", "Canada"),
            ("https://data.gov.au/data/api/3/action/package_search", "Australia"),
            ("https://data.gov.ie/api/3/action/package_search", "Ireland"),
            ("https://data.humdata.org/api/3/action/package_search", "HDX")]


def _on_drive(sink):
    """Files per format already in the Drive folder (2026-11-07: downloads with the same name had overwritten each
    other, so the old download counter said 3,000 while the Drive held 2,008)."""
    import subprocess
    have = {}
    for fmt in TARGET:
        r = subprocess.run(["rclone", "lsf", "-R", "--files-only", f"{sink.remote}/{SHEETS}/{fmt.upper()}", "-q"],
                           capture_output=True, text=True, timeout=900)
        have[fmt] = len(r.stdout.splitlines()) if r.returncode == 0 else 0
    return have


def sheets(sink, st):
    import hashlib
    s = session()
    got = _on_drive(sink) if sink.live else st.setdefault("sheet_count", {k: 0 for k in TARGET})
    print(f"sheets on the Drive: {sum(got.values())} of {TOTAL}")
    seen = set(st.setdefault("sheet_urls", []))
    n = 0
    # first each format up to its share, then any format (one may run out) until the total is reached
    plan = [(fmt, want) for fmt, want in TARGET.items()] + [(fmt, None) for fmt in ("csv", "xlsx", "xls")]
    for fmt, want in plan:
        for api, country in CATALOGS:
            key = f"sheet_start3:{fmt}:{country}"  # 3: scanned again for the files the overwrites lost
            while (got[fmt] < want if want else sum(got.values()) < TOTAL) and sum(got.values()) < TOTAL and not sink.full():
                start = st.get(key, 0)
                r = get(s, api, params={"fq": f'res_format:"{fmt.upper()}"', "rows": 50, "start": start,
                                        "sort": "metadata_modified desc"})
                results = ((r.json().get("result") or {}).get("results") or []) if r else []
                st[key] = start + 50
                if not results:
                    break
                for pkg in results:
                    org = safe(((pkg.get("organization") or {}).get("title") or "Other").split(" | ")[0], 60)  # "EN | FR" titles
                    for res in pkg.get("resources") or []:
                        url = res.get("url") or ""
                        if (res.get("format") or "").lower().strip(". ") != fmt or url in seen:
                            continue
                        seen.add(url)
                        st["sheet_urls"].append(url)
                        title = safe(res.get("name") or pkg.get("title") or "data", 90)
                        if not english(f"{pkg.get('title') or ''} {title}"):
                            continue
                        tag = hashlib.md5(url.encode()).hexdigest()[:6]  # same-named files never overwrite each other
                        rel = f"{SHEETS}/{fmt.upper()}/{country} - {org}/{title} {tag}.{fmt}"
                        if download(s, url, CAP, sink, rel, MAGIC[fmt], timeout=25):
                            got[fmt] += 1
                            n += 1
                        break  # one file per dataset keeps the collection varied
                    if (want and got[fmt] >= want) or sum(got.values()) >= TOTAL or sink.full():
                        break
    return n


SOURCES = {"sheets": sheets}
