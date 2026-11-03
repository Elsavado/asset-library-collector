"""Write the studio world into Notion under the shared root page. Resumable: every created object is keyed in
the state file, so a rerun skips what exists. Logs print counts only (the repository is public)."""
import datetime as dt
import json
import os
import time

import requests

from . import content as C
from .sections import SECTIONS, page_blocks, special_blocks
from .world import ROLES, STUDIO, TODAY, World, d

API = "https://api.notion.com/v1"


class Notion:
    def __init__(self, token, dry=False):
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28",
                               "Content-Type": "application/json"})
        self.dry = dry
        self.last = 0.0
        self.calls = 0
        self.fake = 0

    def req(self, method, path, body=None):
        if self.dry:
            self.fake += 1
            return {"id": f"dry-{self.fake}"}
        for attempt in range(8):
            wait = 0.34 - (time.time() - self.last)  # ~3 requests per second
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            self.calls += 1
            try:
                r = self.s.request(method, API + path, data=json.dumps(body) if body is not None else None, timeout=60)
            except requests.RequestException:
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", 2)) + 0.5)
                continue
            if r.status_code in (409, 500, 502, 503, 504):
                time.sleep(3 * (attempt + 1))
                continue
            raise RuntimeError(f"Notion {method} {path.split('/')[1]} -> {r.status_code}: "
                               f"{r.json().get('code', '')} {r.json().get('message', '')[:300]}")
        raise RuntimeError(f"Notion {method} gave up after retries")


# ---- block conversion ------------------------------------------------------------------------------------
def rt(text, bold=False):
    text = str(text)
    out = []
    for i in range(0, max(1, len(text)), 1900):
        o = {"type": "text", "text": {"content": text[i:i + 1900]}}
        if bold:
            o["annotations"] = {"bold": True}
        out.append(o)
    return out


def block(b):
    k = b[0]
    if k in ("h2", "h3"):
        t = "heading_2" if k == "h2" else "heading_3"
        return {"type": t, t: {"rich_text": rt(b[1])}}
    if k == "p":
        return {"type": "paragraph", "paragraph": {"rich_text": rt(b[1])}}
    if k == "bullet":
        return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rt(b[1])}}
    if k == "num":
        return {"type": "numbered_list_item", "numbered_list_item": {"rich_text": rt(b[1])}}
    if k == "todo":
        return {"type": "to_do", "to_do": {"rich_text": rt(b[1]), "checked": bool(b[2])}}
    if k == "callout":
        return {"type": "callout", "callout": {"rich_text": rt(b[1]), "icon": {"type": "emoji", "emoji": "📌"}}}
    if k == "msg":  # who, date, text: a dated message in a page's discussion
        return {"type": "quote", "quote": {"rich_text": rt(f"{b[1]} · {C.fmt(b[2])}", True) + rt(f"\n{b[3]}")}}
    if k == "bullet_rich":
        return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rt(f"{b[1]}: ", True) + rt(b[2])}}
    if k == "table":
        rows = b[1]
        width = len(rows[0])
        return {"type": "table", "table": {"table_width": width, "has_column_header": True, "has_row_header": False,
                                           "children": [{"type": "table_row", "table_row": {"cells": [rt(c) for c in row]}}
                                                        for row in rows]}}
    if k == "divider":
        return {"type": "divider", "divider": {}}
    raise ValueError(k)


def blocks(bs):
    return [block(b) for b in bs][:100]


# ---- property helpers ------------------------------------------------------------------------------------
def title(t):
    return {"title": rt(t[:1900])}


def text(t):
    return {"rich_text": rt(t)}


def sel(v):
    return {"select": {"name": str(v)[:100].replace(",", " ")}}


def msel(vs):
    return {"multi_select": [{"name": str(v)[:100].replace(",", " ")} for v in vs]}


def date(a, b=None):
    if a is None:
        return {"date": None}
    return {"date": {"start": d(a), **({"end": d(b)} if b else {})}}


def num(v):
    return {"number": v}


def rel(ids):
    return {"relation": [{"id": i} for i in ids if i]}


def opts(names):
    return [{"name": str(n)[:100].replace(",", " ")} for n in dict.fromkeys(names)][:100]


# ---- state -----------------------------------------------------------------------------------------------
class State:
    def __init__(self, path):
        self.path = path
        self.data = {"ids": {}, "complete": False, "comments_ok": True}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.data.update(json.load(f))
        self.dirty = 0

    def get(self, k):
        return self.data["ids"].get(k)

    def put(self, k, v):
        self.data["ids"][k] = v
        self.dirty += 1
        if self.dirty >= 20:
            self.save()

    def save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f)
        os.replace(tmp, self.path)
        self.dirty = 0


class OutOfTime(Exception):
    pass


class Builder:
    def __init__(self, notion, state, root, deadline, scale=1.0):
        self.n, self.st, self.root, self.deadline, self.scale = notion, state, root, deadline, scale
        self.w = World()
        self.made = {}

    def tick(self):
        if time.time() > self.deadline:
            raise OutOfTime()

    def once(self, key, fn):
        got = self.st.get(key)
        if got:
            return got
        self.tick()
        res = fn()
        self.st.put(key, res["id"])
        kind = key.split(":")[0]
        self.made[kind] = self.made.get(kind, 0) + 1
        return res["id"]

    def page(self, key, parent, ttl, emoji, bs):
        return self.once(key, lambda: self.n.req("POST", "/pages", {
            "parent": {"page_id": parent}, "icon": {"type": "emoji", "emoji": emoji},
            "properties": {"title": title(ttl)}, "children": blocks(bs)}))

    def row(self, key, db, props, bs, emoji=None, comments=()):
        def make():
            body = {"parent": {"database_id": self.st.get(f"db:{db}")}, "properties": props, "children": blocks(bs)}
            if emoji:
                body["icon"] = {"type": "emoji", "emoji": emoji}
            res = self.n.req("POST", "/pages", body)
            for c in comments:
                if not self.st.data["comments_ok"]:
                    break
                try:
                    self.n.req("POST", "/comments", {"parent": {"page_id": res["id"]}, "rich_text": rt(c)})
                except RuntimeError as e:
                    if "403" in str(e) or "restricted" in str(e):
                        self.st.data["comments_ok"] = False  # integration lacks the comment capability
                        print("comments: capability not granted, continuing without page comments")
                    else:
                        raise
            return res
        return self.once(key, make)

    def database(self, key, parent, ttl, props):
        return self.once(f"db:{key}", lambda: self.n.req("POST", "/databases", {
            "parent": {"type": "page_id", "page_id": parent}, "is_inline": True,
            "title": rt(ttl), "properties": props}))

    # ---- guard against a lost state file ---------------------------------------------------------------
    def check_fresh(self):
        if self.st.data["ids"] or self.n.dry:
            return
        res = self.n.req("GET", f"/blocks/{self.root}/children?page_size=100")
        names = {s[0] for s in SECTIONS}
        found = [b for b in res.get("results", []) if b.get("type") == "child_page"
                 and b["child_page"].get("title") in names]
        if found:
            raise SystemExit("state is empty but the workspace already has section pages; refusing to duplicate")

    # ---- build -----------------------------------------------------------------------------------------
    def run(self):
        self.check_fresh()
        w = self.w
        people = [p["name"] for p in w.people]
        self.once("root:intro", lambda: self.n.req("PATCH", f"/blocks/{self.root}/children", {"children": blocks([
            ("callout", f"{STUDIO} · visualisation and digital-asset studio · workspace since January 2020"),
            ("p", f"{len(w.people)} people have worked here across {len(w.clients)} clients and "
                  f"{len(w.projects)} projects. Start with the section that matches your work; every project, "
                  f"task, meeting and decision since 2020 is linked from these pages."),
            ("h2", "Sections")] + [("bullet", f"{s[1]} {s[0]}: {s[2]}") for s in SECTIONS])}))

        hosts = {}
        for si, (sec, emoji, intro, pages) in enumerate(SECTIONS):
            sid = self.page(f"section:{si}", self.root, sec, emoji, [
                ("callout", intro), ("p", f"{len(pages)} pages in this section. Each one has an owner, a change "
                                          f"history and the discussion that shaped it.")])
            for pi, (ttl, em, db, owners) in enumerate(pages):
                bs = special_blocks(w, ttl) or ([("callout", f"{ttl}: live database below. Filter by project, "
                                                             f"person or date.")] if db else page_blocks(w, sec, ttl, owners))
                pid = self.page(f"page:{si}:{pi}", sid, ttl, em, bs)
                if db:
                    hosts[db] = pid

        sprints = [s["name"] for s in w.sprints]
        tags = C.TAGS
        self.database("people", hosts["people"], "Team directory", {
            "Name": {"title": {}}, "Role": {"select": {"options": opts(r for _, r, _ in ROLES)}},
            "Department": {"select": {}}, "Office": {"select": {}}, "Start date": {"date": {}},
            "End date": {"date": {}}, "Status": {"select": {"options": opts(["Active", "Alumni"])}}})
        self.database("clients", hosts["clients"], "Clients", {
            "Name": {"title": {}}, "Industry": {"select": {}}, "City": {"select": {}}, "Client since": {"date": {}},
            "Account lead": {"select": {}}, "Projects": {"number": {}}, "Lifetime value": {"number": {"format": "dollar"}}})
        cl = self.st.get("db:clients")
        self.database("projects", hosts["projects"], "Project portfolio", {
            "Name": {"title": {}}, "Code": {"rich_text": {}}, "Client": {"relation": {"database_id": cl, "single_property": {}}},
            "Type": {"select": {}}, "Status": {"select": {"options": opts(["Planned", "In progress", "At risk", "Delivered", "Cancelled"])}},
            "Lead": {"select": {"options": opts(people)}}, "Producer": {"select": {"options": opts(people)}},
            "Team": {"multi_select": {"options": opts(people)}}, "Timeline": {"date": {}},
            "Budget": {"number": {"format": "dollar"}}, "Spent": {"number": {"format": "dollar"}},
            "Priority": {"select": {}}, "Asset Library folders": {"multi_select": {}}})
        pr = self.st.get("db:projects")
        self.database("sprints", hosts["sprints"], "Sprints", {
            "Name": {"title": {}}, "Dates": {"date": {}}, "Goal": {"rich_text": {}}, "Velocity": {"number": {}},
            "Projects active": {"number": {}}})
        self.database("tasks", hosts["tasks"], "Tasks", {
            "Task": {"title": {}}, "Project": {"relation": {"database_id": pr, "single_property": {}}},
            "Status": {"select": {"options": opts(["Backlog", "To do", "In progress", "In review", "Blocked", "Done", "Won't do"])}},
            "Assignees": {"multi_select": {"options": opts(people)}}, "Reviewer": {"select": {"options": opts(people)}},
            "Priority": {"select": {"options": opts(["High", "Medium", "Low"])}}, "Sprint": {"select": {}},
            "Created on": {"date": {}}, "Due": {"date": {}}, "Completed": {"date": {}}, "Points": {"number": {}},
            "Tags": {"multi_select": {"options": opts(tags)}}, "Format": {"select": {}}})
        self.database("meetings", hosts["meetings"], "Meeting notes", {
            "Meeting": {"title": {}}, "Project": {"relation": {"database_id": pr, "single_property": {}}},
            "Date": {"date": {}}, "Type": {"select": {"options": opts(C.MEET_TYPES + ["All-hands"])}},
            "Attendees": {"multi_select": {}}, "Facilitator": {"select": {}}})
        self.database("docs", hosts["docs"], "Docs & specs", {
            "Document": {"title": {}}, "Project": {"relation": {"database_id": pr, "single_property": {}}},
            "Type": {"select": {}}, "Date": {"date": {}}, "Author": {"select": {}}, "Reviewers": {"multi_select": {}},
            "Status": {"select": {}}, "Version": {"rich_text": {}}})
        self.database("decisions", hosts["decisions"], "Decision log", {
            "Decision": {"title": {}}, "Project": {"relation": {"database_id": pr, "single_property": {}}},
            "Date": {"date": {}}, "Owner": {"select": {}}, "Status": {"select": {}}, "Impact": {"select": {}}})
        self.database("assets", hosts["assets"], "Asset register", {
            "Asset": {"title": {}}, "Project": {"relation": {"database_id": pr, "single_property": {}}},
            "Category": {"select": {}}, "Format": {"select": {}}, "Status": {"select": {}}, "Version": {"number": {}},
            "Owner": {"select": {}}, "Created on": {"date": {}}, "Updated on": {"date": {}},
            "Size (MB)": {"number": {}}, "Polygons": {"number": {}}, "Asset Library path": {"rich_text": {}}})
        self.database("weekly", hosts["weekly"], "Weekly updates", {
            "Update": {"title": {}}, "Week of": {"date": {}}, "Author": {"select": {}}, "Active projects": {"number": {}}})
        self.database("okrs", hosts["okrs"], "OKRs", {
            "Objective": {"title": {}}, "Quarter": {"select": {}}, "Owner": {"select": {}}, "Score": {"number": {"format": "percent"}}})
        self.database("finance", hosts["finance"], "Monthly spend reviews", {
            "Month": {"title": {}}, "Period": {"date": {}}, "Total spend": {"number": {"format": "dollar"}},
            "Budget": {"number": {"format": "dollar"}}, "Variance": {"number": {"format": "dollar"}},
            "Active projects": {"number": {}}, **{k: {"number": {"format": "dollar"}} for k in
                                                  ["Software & subscriptions", "Render farm & cloud", "Contractors", "Travel"]}})

        # ---- rows: people, clients, projects -------------------------------------------------------------
        for i, p in enumerate(w.people):
            self.row(f"person:{i}", "people", {
                "Name": title(p["name"]), "Role": sel(p["role"]), "Department": sel(p["dept"]), "Office": sel(p["office"]),
                "Start date": date(p["start"]), "End date": date(p["end"]),
                "Status": sel("Alumni" if p["end"] else "Active")}, [
                ("p", f"{p['name']} joined {STUDIO} on {C.fmt(p['start'])} as {p['role']} ({p['dept']}), based in {p['office']}."
                      + (f" Left on {C.fmt(p['end'])}." if p["end"] else "")),
                ("h3", "Projects"),
                *[("bullet", f"{x['code']} {x['name']} ({x['start'].year})") for x in w.projects if p["name"] in x["team"]][:40]])
        for i, c in enumerate(w.clients):
            ps = [x for x in w.projects if x["client"] == c["name"]]
            lead = C.rng("cl", i).choice(w.staff(c["since"], "Client Services") or w.staff(c["since"], "Leadership"))["name"]
            self.row(f"client:{i}", "clients", {
                "Name": title(c["name"]), "Industry": sel(c["industry"]), "City": sel(c["city"]),
                "Client since": date(c["since"]), "Account lead": sel(lead), "Projects": num(len(ps)),
                "Lifetime value": num(sum(x["spent"] for x in ps if x["status"] != "Planned"))}, [
                ("p", f"{c['name']} ({c['industry']}, {c['city']}) has worked with {STUDIO} since {C.fmt(c['since'])}. Account lead: {lead}."),
                ("h3", "Engagements"), *[("bullet", f"{x['code']} {x['name']}: {x['status']}") for x in ps][:40]])
        for p in w.projects:
            ci = next((i for i, c in enumerate(w.clients) if c["name"] == p["client"]), None)
            r = C.rng("proj", p["id"])
            bs = [("callout", f"{p['code']} · {p['label']} · {p['status']} · lead {p['lead']} · producer {p['producer']}"),
                  ("h2", "Overview"),
                  ("p", f"{p['name']} {'for ' + p['client'] if p['client'] else '(internal)'} ran from {C.fmt(p['start'])} "
                        f"to {C.fmt(p['end'])}. Deliverables are stored in " + ", ".join(f"Asset Library / {f}" for f in p["folders"]) + "."),
                  ("h2", "Team"), *[("bullet", n) for n in p["team"]],
                  ("h2", "Milestones"),
                  ("table", [["Milestone", "Date", "Owner"]] + [[m, C.fmt(C.clamp(p["start"] + dt.timedelta(days=int(f * (p["end"] - p["start"]).days)))),
                                                                  r.choice(p["team"])] for m, f in
                                                                 [("Kickoff", 0), ("Look approved", .25), ("First client drop", .45),
                                                                  ("Round 2 feedback", .65), ("Final delivery", 1)]]),
                  ("h2", "Project log")]
            bs += [("msg", who, day, txt) for who, day, txt in C.discussion(r, p, w, p["start"], r.randint(6, 12))]
            self.row(f"project:{p['id']}", "projects", {
                "Name": title(p["name"]), "Code": text(p["code"]), "Client": rel([self.st.get(f"client:{ci}")] if ci is not None else []),
                "Type": sel(p["label"]), "Status": sel(p["status"]), "Lead": sel(p["lead"]), "Producer": sel(p["producer"]),
                "Team": msel(p["team"]), "Timeline": date(p["start"], p["end"]), "Budget": num(p["budget"]),
                "Spent": num(p["spent"]), "Priority": sel(p["priority"]), "Asset Library folders": msel(p["folders"])},
                bs, comments=C.comments(r, p, p["start"], .6))
        for s in w.sprints:
            live = [p for p in w.projects if p["start"] <= s["end"] and p["end"] >= s["start"]]
            r = C.rng("sprint", s["n"])
            self.row(f"sprint:{s['n']}", "sprints", {
                "Name": title(s["name"]), "Dates": date(s["start"], s["end"]),
                "Goal": text(f"Ship {r.choice(live)['name'] if live else 'internal tooling'} milestone and clear review backlog"),
                "Velocity": num(r.randint(40, 140)), "Projects active": num(len(live))}, [
                ("p", f"{s['name']}: {C.fmt(s['start'])} to {C.fmt(s['end'])}. {len(live)} projects active."),
                *[("bullet", f"{p['code']} {p['name']}") for p in live][:20]])

        # ---- per-project work: tasks, meetings, docs, decisions, assets ----------------------------------
        for p in w.projects:
            pid = self.st.get(f"project:{p['id']}")
            if p["start"] > TODAY:
                continue
            n_tasks = int(max(20, p["months"] * 28) * self.scale)
            for i in range(n_tasks):
                t = C.task(w, p, i)
                self.row(f"task:{p['id']}:{i}", "tasks", {
                    "Task": title(t["title"]), "Project": rel([pid]), "Status": sel(t["status"]),
                    "Assignees": msel(t["assignees"]), "Reviewer": sel(t["reviewer"]), "Priority": sel(t["priority"]),
                    "Sprint": sel(t["sprint"]), "Created on": date(t["created"]), "Due": date(t["due"]),
                    "Completed": date(t["done"]), "Points": num(t["points"]), "Tags": msel(t["tags"]),
                    "Format": sel(t["format"])}, t["blocks"], comments=t["comments"])
            for i, (day, kind) in enumerate(self.meeting_dates(p)):
                m = C.meeting(w, p, i, day, kind)
                self.row(f"meeting:{p['id']}:{i}", "meetings", {
                    "Meeting": title(m["title"]), "Project": rel([pid]), "Date": date(m["date"]), "Type": sel(m["type"]),
                    "Attendees": msel(m["attendees"]), "Facilitator": sel(m["facilitator"])}, m["blocks"], comments=m["comments"])
            for i in range(int((7 + p["months"] // 2) * min(1, self.scale * 2))):
                x = C.doc(w, p, i)
                self.row(f"doc:{p['id']}:{i}", "docs", {
                    "Document": title(x["title"]), "Project": rel([pid]), "Type": sel(x["type"]), "Date": date(x["date"]),
                    "Author": sel(x["author"]), "Reviewers": msel(x["reviewers"]), "Status": sel(x["status"]),
                    "Version": text(x["version"])}, x["blocks"], comments=x["comments"])
            for i in range(int((4 + p["months"]) * min(1, self.scale * 2))):
                x = C.decision(w, p, i)
                self.row(f"decision:{p['id']}:{i}", "decisions", {
                    "Decision": title(x["title"]), "Project": rel([pid]), "Date": date(x["date"]), "Owner": sel(x["owner"]),
                    "Status": sel(x["status"]), "Impact": sel(x["impact"])}, x["blocks"])
            for i in range(int(p["months"] * 18 * self.scale)):
                a = C.asset(w, p, i)
                self.row(f"asset:{p['id']}:{i}", "assets", {
                    "Asset": title(a["title"]), "Project": rel([pid]), "Category": sel(a["category"]), "Format": sel(a["format"]),
                    "Status": sel(a["status"]), "Version": num(a["version"]), "Owner": sel(a["owner"]),
                    "Created on": date(a["created"]), "Updated on": date(a["updated"]), "Size (MB)": num(a["size"]),
                    "Polygons": num(a["polys"]), "Asset Library path": text(a["path"])}, a["blocks"])
            print(f"project {p['id']} done; created so far {self.summary()}")

        # ---- studio-wide series --------------------------------------------------------------------------
        wk = C.dt.date(2020, 1, 6)
        i = 0
        while wk <= TODAY:
            x = C.weekly(w, wk, i)
            self.row(f"weekly:{i}", "weekly", {"Update": title(x["title"]), "Week of": date(x["date"]),
                                               "Author": sel(x["author"]), "Active projects": num(x["active"])}, x["blocks"])
            wk += dt.timedelta(days=7)
            i += 1
        for y in range(2020, TODAY.year + 1):
            for q in range(1, 5):
                if dt.date(y, 3 * q - 2, 1) > TODAY:
                    continue
                for x in C.okrs(w, y, q):
                    self.row(f"okr:{y}:{q}:{x['k']}", "okrs", {"Objective": title(x["title"]), "Quarter": sel(x["quarter"]),
                                                              "Owner": sel(x["owner"]), "Score": num(x["score"])}, x["blocks"])
        y, m = 2020, 1
        while dt.date(y, m, 1) <= TODAY.replace(day=1):
            x = C.finance_month(w, y, m)
            self.row(f"finance:{y}:{m}", "finance", {
                "Month": title(x["title"]), "Period": date(x["month"]), "Total spend": num(x["total"]),
                "Budget": num(x["budget"]), "Variance": num(x["budget"] - x["total"]), "Active projects": num(x["active"]),
                **{k: num(x["cats"][k]) for k in ["Software & subscriptions", "Render farm & cloud", "Contractors", "Travel"]}},
                x["blocks"])
            m += 1
            if m == 13:
                y, m = y + 1, 1
        self.st.data["complete"] = True

    def meeting_dates(self, p):
        out = []
        day = p["start"]
        out.append((day, "Kickoff"))
        k = 0
        end = min(p["end"], TODAY)
        while True:
            day += dt.timedelta(days=7)
            if day > end:
                break
            k += 1
            out.append((day, "Design review" if p["kind"] in ("arch", "auto", "asset", "brand", "cad") else "Technical review"))
            if k % 2 == 0:
                out.append((day + dt.timedelta(days=1), "Client call" if p["client"] else "Sprint planning"))
            if k % 2 == 1:
                out.append((day + dt.timedelta(days=2), "Render review" if p["kind"] in ("arch", "auto") else "Standup"))
            if k % 4 == 0:
                out.append((day + dt.timedelta(days=3), "Retrospective"))
        return [(x, t) for x, t in out if x <= TODAY]

    def summary(self):
        return ", ".join(f"{k} {v}" for k, v in sorted(self.made.items()))
