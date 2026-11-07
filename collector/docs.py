"""Documents: .pdf, .txt, .docx, .doc and .dwg files, about 220,000 in all.

Sources: NASA technical reports (NTRS, PDF + plain-text), Federal Register documents (PDF + plain-text),
Project Gutenberg books in English (plain-text, from a mirror), and Word, PDF and DWG files published on
public-sector websites (.gov, .edu, .mil, .int and government domains abroad) taken from the Common Crawl
archive through its columnar index. Each source stops at its own quota, so the total lands near 220,000.
Files are fetched 12 at a time."""
import csv
import gzip
import html
import io
import os
import random
import re
import zlib

from .common import get, safe, session
from .util import POOL, fetch_many, not_html

DOCS = "08 Documents"
TYPE = {"pdf": "PDF", "txt": "TXT", "docx": "DOCX", "doc": "DOC", "dwg": "DWG"}
CAP = 40 * 2 ** 20
# 2026-11-07: the folder cap (211,000 files) decides when to stop
QUOTA = {"ntrs": 150000, "fedreg": 150000, "gutenberg": 60000, "commoncrawl": 60000}

is_pdf = lambda h: h[:5] == b"%PDF-"


def html_text(body):
    """NTRS serves its text versions wrapped in HTML: keep the words, one block per line."""
    t = body.decode("utf-8", "replace")
    t = re.sub(r"(?is)<(head|script|style)\b.*?</\1>", "", t)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|h\d|li|tr|pre)>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    t = re.sub(r"\n\s*\n\s*\n+", "\n\n", t).strip()
    return t.encode("utf-8") if len(t) > 200 else None


def _left(st, src):
    return QUOTA[src] - st.get("added", 0)


def _fetch(sink, st, items):
    got = len(fetch_many(sink, items))
    st["added"] = st.get("added", 0) + got
    return got


def ntrs(sink, st):
    """NASA Technical Reports Server: each report as its PDF and its plain-text version, year by year
    (newest first). The search API pages at most 10,000 records per query, so each year is its own query."""
    s = session()
    base = "https://ntrs.nasa.gov"
    st.setdefault("year", 2026)
    n = 0
    while st["year"] >= 1917 and _left(st, "ntrs") > 0 and not sink.full():
        year, start = st["year"], st.get("from", 0)
        r = get(s, f"{base}/api/citations/search", params={
            "page.size": 100, "page.from": start, "published.gte": f"{year}-01-01", "published.lte": f"{year}-12-31"})
        rows = (r.json().get("results") or []) if r else []
        items = []
        for rec in rows:
            title = safe(rec.get("title") or rec["id"], 90)
            for d in (rec.get("downloads") or [])[:1]:  # the first file of a record is the report itself
                links = d.get("links") or {}
                rel = f"NASA Technical Reports/{year}/{title} {rec['id']}"
                if links.get("pdf"):
                    items.append((base + links["pdf"], CAP, f"{DOCS}/PDF/{rel}.pdf", is_pdf))
                if links.get("fulltext"):
                    items.append((base + links["fulltext"], CAP, f"{DOCS}/TXT/{rel}.txt", None, html_text))
        n += _fetch(sink, st, items)
        if len(rows) < 100 or start + 100 >= 10000:
            st["year"], st["from"] = year - 1, 0
        else:
            st["from"] = start + 100
    return n


def fedreg(sink, st):
    """Federal Register (2019 onward, newest first): every rule, notice and presidential document as its
    PDF and its plain-text version, month by month."""
    s = session()
    ym = st.setdefault("ym", [2026, 11])
    n = 0
    while ym[0] >= 2019 and _left(st, "fedreg") > 0 and not sink.full():
        y, m = ym
        last = (28 if m == 2 else 30 if m in (4, 6, 9, 11) else 31)
        page = st.get("page", 1)
        r = get(s, "https://www.federalregister.gov/api/v1/documents.json", params=[
            ("per_page", 200), ("page", page), ("order", "oldest"),
            ("conditions[publication_date][gte]", f"{y}-{m:02d}-01"),
            ("conditions[publication_date][lte]", f"{y}-{m:02d}-{last}"),
            ("fields[]", "document_number"), ("fields[]", "title"), ("fields[]", "type"),
            ("fields[]", "pdf_url"), ("fields[]", "raw_text_url")])
        d = r.json() if r else {}
        items = []
        for doc in d.get("results") or []:
            folder = f"Federal Register/{y}-{m:02d} {safe(doc.get('type') or 'Document', 30)}"
            name = f"{safe(doc.get('title') or doc['document_number'], 90)} {doc['document_number']}"
            if doc.get("pdf_url"):
                items.append((doc["pdf_url"], CAP, f"{DOCS}/PDF/{folder}/{name}.pdf", is_pdf))
            if doc.get("raw_text_url"):
                items.append((doc["raw_text_url"], CAP, f"{DOCS}/TXT/{folder}/{name}.txt", not_html))
        n += _fetch(sink, st, items)
        if page < min(d.get("total_pages") or 0, 50):
            st["page"] = page + 1
        else:
            st["page"] = 1
            ym[:] = [y - 1, 12] if m == 1 else [y, m - 1]
    return n


def gutenberg(sink, st):
    """Project Gutenberg books in English as plain text, fetched from a PGLAF mirror (the main site asks
    robots to use mirrors), filed by the first letter of the author."""
    s = session()
    r = get(s, "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv", timeout=600)
    if not r:
        return 0
    books = [b for b in csv.DictReader(io.StringIO(r.content.decode("utf-8", "replace")))
             if b.get("Type") == "Text" and (b.get("Language") or "").strip() == "en"]
    n = 0
    while st.get("i", 0) < len(books) and _left(st, "gutenberg") > 0 and not sink.full():
        i = st.get("i", 0)
        items = []
        for b in books[i:i + 48]:
            num = b["Text#"]
            author = (b.get("Authors") or "Anonymous").split(";")[0].split(",")[0].strip() or "Anonymous"
            letter = author[0].upper() if author[0].isalpha() else "#"
            items.append((f"https://aleph.pglaf.org/cache/epub/{num}/pg{num}.txt", CAP, f"{DOCS}/TXT/Project Gutenberg/"
                          f"{letter}/{safe(b.get('Title') or num, 90)} - {safe(author, 40)} {num}.txt", not_html))
        st["i"] = i + len(items)
        n += _fetch(sink, st, items)
    return n


CC = "https://data.commoncrawl.org"
CRAWLS = ["CC-MAIN-2025-08", "CC-MAIN-2024-51", "CC-MAIN-2024-46", "CC-MAIN-2024-42", "CC-MAIN-2024-38",
          "CC-MAIN-2024-33", "CC-MAIN-2024-30", "CC-MAIN-2024-26", "CC-MAIN-2024-22", "CC-MAIN-2024-18"]
MIME = {"application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/msword": "doc", "application/pdf": "pdf", "image/vnd.dwg": "dwg", "application/acad": "dwg",
        "application/x-dwg": "dwg", "image/x-dwg": "dwg"}
PUBLIC = re.compile(r"\.(gov|edu|mil|int)$|\.(gov|gc|ac|edu)\.[a-z]{2}$|\.nhs\.uk$|\.europa\.eu$", re.I)
MAGIC = {"pdf": is_pdf, "docx": lambda h: h[:2] == b"PK", "doc": lambda h: h[:4] == b"\xd0\xcf\x11\xe0",
         "dwg": lambda h: h[:4] == b"AC10"}
# PDFs are plentiful; Word and DWG files are rarer, so a part file contributes at most this many PDFs
PDF_PER_PART = 150


def _cc_part(s, path, cache="cache/cc-part.parquet"):
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    os.makedirs("cache", exist_ok=True)
    with s.get(f"{CC}/{path}", stream=True, timeout=900) as r:
        r.raise_for_status()
        with open(cache, "wb") as f:
            for chunk in r.iter_content(8 << 20):
                f.write(chunk)
    try:
        t = pq.read_table(cache, columns=["url", "url_host_name", "content_mime_detected", "content_languages",
                                          "fetch_status", "warc_filename", "warc_record_offset",
                                          "warc_record_length", "content_truncated"],
                          filters=[("content_mime_detected", "in", list(MIME)), ("fetch_status", "=", 200)])
    finally:
        os.remove(cache)
    t = t.filter(pc.is_null(t["content_truncated"]))
    return [row for row in t.to_pylist() if PUBLIC.search(row["url_host_name"] or "")
            and (MIME[row["content_mime_detected"]] == "dwg" or "eng" in (row["content_languages"] or "eng"))]


def _warc_body(row):
    """One record from a WARC file by byte range; returns the HTTP body."""
    off, ln = int(row["warc_record_offset"]), int(row["warc_record_length"])
    try:
        r = get(session(), f"{CC}/{row['warc_filename']}", headers={"Range": f"bytes={off}-{off + ln - 1}"}, tries=3)
        if r is None or len(r.content) != ln:
            return None
        rec = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(r.content)
    except Exception:
        return None
    parts = rec.split(b"\r\n\r\n", 2)  # WARC headers, HTTP headers, body
    return parts[2] if len(parts) == 3 else None


def commoncrawl(sink, st):
    """Word (.docx, .doc), PDF and DWG files from public-sector websites in English, out of recent Common
    Crawl archives: one index part file at a time, every Word and DWG file in it and up to PDF_PER_PART PDFs."""
    s = session()
    pos = st.setdefault("cc", {"crawl": 0, "part": 0})
    n = 0
    while pos["crawl"] < len(CRAWLS) and _left(st, "commoncrawl") > 0 and not sink.full():
        crawl = CRAWLS[pos["crawl"]]
        r = get(s, f"{CC}/crawl-data/{crawl}/cc-index-table.paths.gz")
        parts = [p for p in gzip.decompress(r.content).decode().split() if "subset=warc/" in p] if r else []
        random.Random(crawl).shuffle(parts)  # spread over the whole crawl, not one slice of it
        if pos["part"] >= len(parts):
            pos["crawl"], pos["part"] = pos["crawl"] + 1, 0
            continue
        try:
            rows = _cc_part(s, parts[pos["part"]])
        except Exception as exc:
            print(f"commoncrawl: index part skipped ({type(exc).__name__})")
            rows = []
        pos["part"] += 1
        pdf = [x for x in rows if MIME[x["content_mime_detected"]] == "pdf"]
        rows = [x for x in rows if MIME[x["content_mime_detected"]] != "pdf"] + pdf[:PDF_PER_PART]
        rows = rows[:max(0, _left(st, "commoncrawl"))]
        for row, body in zip(rows, POOL.map(_warc_body, rows)):
            kind = MIME[row["content_mime_detected"]]
            if not body or len(body) > CAP or not MAGIC[kind](body[:8]):
                continue
            host = row["url_host_name"].lower().removeprefix("www.")
            fname = safe(row["url"].split("?")[0].rstrip("/").rsplit("/", 1)[-1], 100)
            if not fname.lower().endswith("." + kind):
                fname = f"{fname}.{kind}"
            sink.write_bytes(f"{DOCS}/{TYPE[kind]}/Public Sector Websites/{safe(host, 60)}/{fname}", body)
            n += 1
            st["added"] = st.get("added", 0) + 1
        sink.state.save()
    return n


SOURCES = {"ntrs": ntrs, "fedreg": fedreg, "gutenberg": gutenberg, "commoncrawl": commoncrawl}
