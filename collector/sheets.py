"""3,000 spreadsheets (.xlsx .xls .csv) from English-language government open-data catalogues (UK, Canada,
Australia, Ireland, UN OCHA HDX): about 1,200 XLSX, 600 XLS and 1,200 CSV, filed by format, then publishing
organisation."""
from .common import english, get, safe, session
from .util import SHEETS, download, not_html

TARGET = {"xlsx": 1200, "xls": 600, "csv": 1200}
CAP = 100 * 2 ** 20
MAGIC = {"xlsx": lambda h: h[:2] == b"PK", "xls": lambda h: h[:4] == b"\xd0\xcf\x11\xe0",
         "csv": lambda h: not_html(h) and b"," in h}
CATALOGS = [("https://ckan.publishing.service.gov.uk/api/action/package_search", "UK"),
            ("https://open.canada.ca/data/api/action/package_search", "Canada"),
            ("https://data.gov.au/data/api/3/action/package_search", "Australia"),
            ("https://data.gov.ie/api/3/action/package_search", "Ireland"),
            ("https://data.humdata.org/api/3/action/package_search", "HDX")]


def sheets(sink, st):
    s = session()
    got = st.setdefault("sheet_count", {k: 0 for k in TARGET})
    seen = set(st.setdefault("sheet_urls", []))
    n = 0
    for fmt, want in TARGET.items():
        for api, country in CATALOGS:
            key = f"sheet_start2:{fmt}:{country}"  # 2: the old US/UK endpoints are gone
            while got[fmt] < want and not sink.full():
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
                        rel = f"{SHEETS}/{fmt.upper()}/{country} - {org}/{title}.{fmt}"
                        if download(s, url, CAP, sink, rel, MAGIC[fmt], timeout=25):
                            got[fmt] += 1
                            n += 1
                        break  # one file per dataset keeps the collection varied
                    if got[fmt] >= want or sink.full():
                        break
    return n


SOURCES = {"sheets": sheets}
