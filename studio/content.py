"""Seeded page content for the studio workspace. Every generator takes (world, project, index) and returns a
plain dict (title, fields, blocks, comments) that build.py turns into Notion API payloads."""
import datetime as dt
import hashlib
import random

from .world import STUDIO, TODAY, d

# ---- phrase banks per work kind --------------------------------------------------------------------------
OBJ = {
    "arch": ["facade glazing", "lobby atrium", "podium retail frontage", "roof terrace", "parking podium",
             "street-level landscaping", "curtain wall mullions", "night lighting pass", "aerial context model",
             "interior amenity floor", "site massing", "pedestrian bridge", "sun-path study", "entrance canopy"],
    "auto": ["front fascia", "wheel set", "headlamp internals", "paint shader library", "interior dashboard",
             "seat stitching", "badge and trim", "turntable camera rig", "studio HDRI set", "underbody detail",
             "configurator colour matrix", "door panel", "charging port", "brake caliper variants"],
    "asset": ["prop LODs", "texture atlases", "collision meshes", "modular wall kit", "vegetation set",
              "street furniture pack", "vehicle kit", "photogrammetry scans", "USDZ exports", "naming audit",
              "pivot and scale pass", "material library", "GLB compression", "thumbnail renders"],
    "cad": ["STEP assemblies", "DXF floor plans", "IGES surfaces", "tolerance annotations", "layer standard",
            "exploded view", "bill of materials", "mesh tessellation settings", "legacy scans", "title blocks",
            "unit conversion", "FreeCAD parametric parts", "weld details", "plant equipment layout"],
    "brand": ["logo lockups", "colour system", "type scale", "InDesign master pages", "social templates",
              "motion toolkit", "key visual comps", "icon set", "brand guidelines PDF", "AE title sequences",
              "packaging dielines", "event signage", "photo retouching", "brush pack"],
    "data": ["cost per frame model", "render node utilisation", "metadata schema", "CSV export job",
             "licence tracker", "storage forecast", "asset tagging rules", "Drive folder audit", "pivot dashboards",
             "dedupe report", "format inventory", "XLSX templates"],
    "finance": ["card policy", "receipt matching", "expense categories", "GL mapping", "budget owners",
                "month-end accruals", "vendor bills", "reimbursement flow", "spend limits", "audit trail",
                "close checklist", "variance report"],
    "zoom": ["recording retention policy", "transcript cleanup", "client review index", "chat export parser",
             "participant reports", "highlight reels", "consent wording", "searchable archive", "storage tiering"],
    "docs": ["standards register", "PDF OCR pass", "reference index", "glossary", "TXT normalisation",
             "version control rules", "document templates", "retention schedule", "citation format"],
    "pipeline": ["publish tool", "farm submitter", "turntable automation", "USD export", "validation checks",
                 "Blender add-on", "asset browser", "Slack notifier", "versioning service", "CI for tools",
                 "texture baker", "batch converter"],
}
VERB = ["Model", "Retopologise", "UV unwrap", "Texture", "Light", "Render", "Review", "Fix", "Optimise",
        "Export", "Document", "Set up", "Clean up", "Rig", "Composite", "Validate", "Convert", "Prototype",
        "Update", "Package", "QA", "Iterate on", "Block out", "Finalise"]
DELIV = ["for client review", "for round 2 feedback", "for the hero shot", "for the weekly drop",
         "before handoff", "for the configurator build", "for print", "for the launch film", "to spec",
         "for internal QA", "for the milestone deliverable", "per client markup"]
TAGS = ["Modelling", "Texturing", "Lighting", "Rendering", "CAD", "Comp", "Pipeline", "Client feedback",
        "Bug", "QA", "Docs", "Motion", "Data", "Finance", "Research"]
STATUS_DONE = ["Done"] * 9 + ["Won't do"]
DISCUSS = [
    "Pushed v{v} to the review folder. {o} is closer, but the edges still read soft at 4K.",
    "Client markup came back on the {o}. Two changes, both small. I'll take the first one.",
    "Can we lock the {o} before Thursday? Lighting is blocked on it.",
    "Ran it through the validator: 3 warnings, no errors. Naming is fixed now.",
    "I compared against the reference pack and the scale was off by about 2%. Corrected in v{v}.",
    "Looks good to me. Approving so {n} can start the render pass.",
    "Render time per frame dropped from {a} to {b} minutes after the texture atlas change.",
    "Flagging scope creep: the client asked for {o} variants that weren't in the SOW. Raising with {n}.",
    "Pairing on this tomorrow morning. I'll share the screen recording in the channel.",
    "Uploaded the source files to {f}. Exports are next to them.",
    "Agree with the feedback. Reverting the {o} to the previous material and trying a warmer HDRI.",
    "Blocked on the CAD import, so I've asked {n} for the cleaned STEP files.",
    "Tested on the configurator staging build and it holds 60 fps on the target tablet.",
    "Re-exported with the new units. Please re-pull before you continue.",
    "Moved to Done. Final files are in the delivery folder, and the checksum list is attached to the ticket.",
    "Quick note from the client call: they love the direction and want the {o} pushed further.",
    "I'd split this into two tickets. The {o} is bigger than one sprint.",
    "Second pair of eyes needed on the topology around the {o}. Shading artefacts appear at grazing angles.",
]
COMMENTS = [
    "Can someone confirm this matches the latest client markup?",
    "Nice work, this is much cleaner than the last round.",
    "Adding this to Friday's review agenda.",
    "Linked the source files in the delivery folder.",
    "Following up: is this still blocked?",
    "Approved from production side.",
    "I left notes inline. Mostly naming and one lighting tweak.",
    "This is a good candidate for the asset library once the project wraps.",
    "Estimate looks light to me. Can we re-point it in planning?",
    "Client confirmed on the call. Closing the loop here.",
]
MEET_TYPES = ["Design review", "Client call", "Sprint planning", "Standup", "Retrospective", "Kickoff",
              "Technical review", "Render review"]


def rng(*key):
    h = hashlib.sha256("|".join(map(str, key)).encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def fmt(day):
    return f"{day:%b} {day.day}, {day.year}"


def between(r, a, b):
    if b <= a:
        return a
    return a + dt.timedelta(days=r.randint(0, (b - a).days))


def clamp(day):
    return min(day, TODAY)


def objs(p):
    return OBJ.get(p["kind"], OBJ["asset"])


def fill(r, s, p, w, day):
    return s.format(v=r.randint(2, 9), o=r.choice(objs(p)), n=r.choice(p["team"]).split()[0],
                    a=r.randint(18, 45), b=r.randint(6, 17), f=r.choice(p["folders"]))


def discussion(r, p, w, start, n):
    """n dated messages between team members, oldest first, never in the future."""
    out = []
    day = start
    for k in range(n):
        day = clamp(day + dt.timedelta(days=r.randint(0, 4), hours=0))
        who = r.choice(p["team"])
        out.append((who, day, fill(r, r.choice(DISCUSS), p, w, day)))
    return out


# ---- items -----------------------------------------------------------------------------------------------
def task(w, p, i):
    r = rng("task", p["id"], i)
    created = between(r, p["start"], min(p["end"], TODAY))
    due = created + dt.timedelta(days=r.randint(3, 21))
    o = r.choice(objs(p))
    title = f"{r.choice(VERB)} {o} {r.choice(DELIV)}"
    if p["status"] in ("Delivered", "Cancelled") or due < TODAY - dt.timedelta(days=10):
        status = r.choice(STATUS_DONE)
    elif created > TODAY - dt.timedelta(days=5):
        status = r.choice(["Backlog", "To do"])
    else:
        status = r.choice(["To do", "In progress", "In progress", "In review", "Blocked", "Done"])
    assignees = r.sample(p["team"], r.choice([1, 1, 1, 2]))
    reviewer = r.choice([x for x in p["team"] if x not in assignees] or p["team"])
    done_on = clamp(due + dt.timedelta(days=r.randint(-3, 6))) if status == "Done" else None
    talk = discussion(r, p, w, created, r.randint(2, 6))
    blocks = [("h3", "Context"),
              ("p", f"Part of {p['name']} ({p['code']}). {r.choice(['Client', 'Art direction', 'Production', 'QA'])} "
                    f"asked for the {o} to be {r.choice(['tightened up', 'reworked', 'matched to reference', 'optimised', 'finished'])} "
                    f"{r.choice(DELIV)}. Source and exports live in Asset Library / {r.choice(p['folders'])}."),
              ("h3", "Acceptance criteria")]
    for c in r.sample(["Matches the approved reference within tolerance", "Naming follows HVS-NAMING-04",
                       "Exports validated (no missing textures, correct units)", "Reviewed by lead before handoff",
                       "Turntable or preview render attached", "Client markup items all addressed",
                       "Polycount within the agreed budget", "File versions archived in the delivery folder"], 3):
        blocks.append(("bullet", c))
    blocks.append(("h3", "Checklist"))
    for c in r.sample(["Pull latest source", "Block out", "First pass", "Self-review", "Lead review",
                       "Fix notes", "Export", "Upload and link"], 4):
        blocks.append(("todo", c, status == "Done" or r.random() < .4))
    blocks.append(("h3", "Discussion"))
    blocks += [("msg", who, day, text) for who, day, text in talk]
    return {"title": title, "status": status, "assignees": assignees, "reviewer": reviewer,
            "priority": r.choice(["High", "Medium", "Medium", "Low"]), "sprint": w.sprint_for(created),
            "created": created, "due": due, "done": done_on, "points": r.choice([1, 2, 3, 5, 5, 8, 13]),
            "tags": r.sample(TAGS, r.randint(1, 2)), "format": r.choice(p["folders"]).split("/")[-1],
            "blocks": blocks, "comments": comments(r, p, created, .25)}


def comments(r, p, start, chance):
    if r.random() > chance:
        return []
    return [f"{who}, {fmt(day)}: {r.choice(COMMENTS)}" for who, day, _ in discussion(r, p, None, start, r.randint(1, 3))]


def meeting(w, p, i, day, kind):
    r = rng("meet", p["id"], i)
    att = r.sample(p["team"], min(len(p["team"]), r.randint(3, 6)))
    if kind == "Client call" and p["client"]:
        att = att + [f"{p['client']} (client)"]
    host = att[0]
    blocks = [("callout", f"{kind} · {fmt(day)} · facilitated by {host}"), ("h3", "Agenda")]
    for a in r.sample([f"Status of the {o}" for o in objs(p)], 3) + [r.choice(["Risks and blockers", "Next drop",
                                                                               "Budget check", "Open questions"])]:
        blocks.append(("num", a))
    blocks.append(("h3", "Notes"))
    for who, _, text in discussion(r, p, w, day, r.randint(3, 6)):
        blocks.append(("bullet_rich", who, text))
    blocks.append(("h3", "Decisions"))
    for _ in range(r.randint(1, 2)):
        blocks.append(("bullet", r.choice([
            f"Go with option {r.choice('ABC')} for the {r.choice(objs(p))}",
            f"Move the client drop to {fmt(clamp(day + dt.timedelta(days=r.randint(3, 10))))}",
            "Freeze scope for this milestone; new asks go to the change log",
            f"{r.choice(p['team'])} owns the final QA pass", "Keep the current lighting setup, only tweak exposure",
            "Split the render job across two farm pools to hit the deadline"])))
    blocks.append(("h3", "Action items"))
    for _ in range(r.randint(2, 4)):
        own = r.choice(att[:-1] if att[-1].endswith("(client)") else att)
        blocks.append(("todo", f"{own}: {r.choice(VERB).lower()} {r.choice(objs(p))} by "
                               f"{fmt(clamp(day + dt.timedelta(days=r.randint(2, 9))))}", day < TODAY - dt.timedelta(days=7)))
    if r.random() < .3:
        blocks.append(("p", f"Recording and transcript are archived under Asset Library / 06 Zoom Calls."))
    return {"title": f"{kind}: {p['name']} ({fmt(day)})", "date": day, "type": kind, "attendees": att,
            "facilitator": host, "blocks": blocks, "comments": comments(r, p, day, .12)}


DOC_TYPES = [("Creative brief", ["Background", "Objectives", "Audience", "Deliverables", "Timeline"]),
             ("Technical spec", ["Summary", "Inputs", "Pipeline", "Formats & budgets", "Validation", "Open questions"]),
             ("Statement of work", ["Scope", "Out of scope", "Milestones", "Assumptions", "Fees"]),
             ("Lookdev notes", ["Reference", "Materials", "Lighting", "Camera", "Feedback log"]),
             ("Postmortem", ["What went well", "What didn't", "Root causes", "Actions"]),
             ("Delivery checklist", ["Files", "Formats", "Naming", "Sign-off"]),
             ("RFC", ["Problem", "Proposal", "Alternatives", "Rollout", "Decision"])]


def doc(w, p, i):
    r = rng("doc", p["id"], i)
    typ, sections = DOC_TYPES[i % len(DOC_TYPES)] if i < len(DOC_TYPES) else r.choice(DOC_TYPES)
    day = clamp(p["end"] if typ == "Postmortem" else between(r, p["start"], min(p["end"], TODAY)))
    author = r.choice(p["team"])
    blocks = [("callout", f"{typ} · {p['code']} · owner {author} · last reviewed {fmt(clamp(day + dt.timedelta(days=r.randint(0, 30))))}")]
    for s in sections:
        blocks.append(("h2", s))
        for _ in range(r.randint(1, 3)):
            o = r.choice(objs(p))
            blocks.append(("p", r.choice([
                f"The {o} is the main risk for this phase. We budget {r.randint(2, 9)} days, and {r.choice(p['team'])} owns it.",
                f"Deliver the {o} as {r.choice(p['folders']).split('/')[-1]} with a preview render and a validation report.",
                f"Client feedback from round {r.randint(1, 4)} asked for more contrast on the {o}; we agreed to a single revision pass.",
                f"Hand-off happens through Asset Library / {r.choice(p['folders'])}, using the {STUDIO} naming standard.",
                f"We measured the {o} against the approved reference; the deviation is within {r.randint(1, 5)} mm at full scale.",
                f"If the {o} slips, we drop the secondary angle rather than compressing review time.",
                f"Render budget for the {o}: {r.randint(4, 40)} min/frame on the standard farm pool."])))
        if r.random() < .35:
            for _ in range(3):
                blocks.append(("bullet", f"{r.choice(VERB)} {r.choice(objs(p))}"))
    blocks.append(("h2", "Review thread"))
    blocks += [("msg", who, dd, text) for who, dd, text in discussion(r, p, w, day, r.randint(2, 5))]
    return {"title": f"{typ}: {p['name']}" + (f" (rev {i // len(DOC_TYPES) + 1})" if i >= len(DOC_TYPES) else ""),
            "type": typ, "date": day, "author": author,
            "reviewers": r.sample([x for x in p["team"] if x != author], min(2, len(p["team"]) - 1)),
            "status": "Final" if day < TODAY - dt.timedelta(days=20) else r.choice(["Draft", "In review"]),
            "version": f"{r.randint(1, 4)}.{r.randint(0, 9)}", "blocks": blocks,
            "comments": comments(r, p, day, .3)}


def decision(w, p, i):
    r = rng("dec", p["id"], i)
    day = between(r, p["start"], min(p["end"], TODAY))
    o = r.choice(objs(p))
    opt = r.sample(["bake lighting", "real-time renderer", "path-traced stills", "outsourced modelling",
                    "in-house modelling", "reuse library assets", "new hero asset", "split delivery",
                    "single final delivery", "higher polycount", "aggressive LODs", "client-supplied CAD",
                    "re-modelled from drawings"], 2)
    title = f"{o.capitalize()}: {opt[0]} over {opt[1]}"
    owner = r.choice(p["team"])
    blocks = [("h3", "Context"), ("p", f"We needed a call on the {o} before {fmt(clamp(day + dt.timedelta(days=r.randint(3, 14))))}. "
                                       f"Both options were prototyped by {r.choice(p['team'])}."),
              ("h3", "Options considered"), ("bullet", f"{opt[0].capitalize()}: faster to iterate, lower risk on the deadline"),
              ("bullet", f"{opt[1].capitalize()}: higher ceiling, but needs {r.randint(3, 12)} more artist-days"),
              ("h3", "Outcome"), ("p", f"Chose {opt[0]}. {owner} owns follow-through; we revisit at the next milestone."),
              ("h3", "Discussion")]
    blocks += [("msg", who, dd, text) for who, dd, text in discussion(r, p, w, day, r.randint(2, 4))]
    return {"title": title, "date": day, "owner": owner,
            "status": r.choice(["Accepted"] * 6 + ["Superseded", "Reverted"]) if day < TODAY - dt.timedelta(days=30)
            else r.choice(["Proposed", "Accepted"]), "impact": r.choice(["High", "Medium", "Low"]), "blocks": blocks}


def asset(w, p, i):
    r = rng("asset", p["id"], i)
    folder = r.choice(p["folders"])
    fmt_ = folder.split("/")[-1]
    o = r.choice(objs(p)).title().replace(" ", "")
    created = between(r, p["start"], min(p["end"], TODAY))
    ver = r.randint(1, 12)
    status = "Delivered" if p["status"] == "Delivered" else r.choice(["WIP", "In review", "Approved"])
    if p["status"] == "Delivered" and r.random() < .3:
        status = "Archived"
    cat = {"01": "3D model", "02": "CAD drawing", "03": "Image", "04": "Spreadsheet", "05": "Finance data",
           "06": "Recording", "07": "Adobe file", "08": "Document"}[folder[:2]]
    size = round(r.uniform(.2, 900 if cat in ("3D model", "Recording") else 120), 1)
    return {"title": f"{p['code']}_{o}_v{ver:03d}", "category": cat, "format": fmt_, "status": status,
            "version": ver, "owner": r.choice(p["team"]), "created": created,
            "updated": clamp(created + dt.timedelta(days=r.randint(0, 60))), "size": size,
            "polys": r.randint(2, 4000) * 1000 if cat == "3D model" else None,
            "path": f"Asset Library / {folder}", "blocks": [
                ("p", f"{cat} for {p['name']}. Version {ver}, owner {r.choice(p['team'])}."),
                ("bullet", f"Source: Asset Library / {folder}"),
                ("bullet", f"Review: {r.choice(['approved by lead', 'client approved', 'pending art direction', 'QA passed'])}"),
                ("bullet", f"Notes: {r.choice(['textures packed', 'units in metres', 'LOD0-LOD3 included', 'layered PSD', 'CMYK + RGB exports', 'transcript attached'])}")]}


def weekly(w, week_start, i):
    r = rng("weekly", i)
    live = [p for p in w.projects if p["start"] <= week_start <= p["end"]] or w.projects[:2]
    author = r.choice(w.staff(week_start, "Production") or w.staff(week_start, "Leadership"))["name"]
    blocks = [("callout", f"Week of {fmt(week_start)} · {len(live)} active projects · written by {author}"),
              ("h2", "Highlights")]
    for p in r.sample(live, min(4, len(live))):
        blocks.append(("bullet", f"{p['name']}: {r.choice(['client approved round', 'hit the milestone drop', 'render pass finished', 'kickoff done', 'scope confirmed', 'QA clean'])} "
                                 f"({r.choice(p['team']).split()[0]})"))
    blocks.append(("h2", "Risks"))
    for p in r.sample(live, min(2, len(live))):
        blocks.append(("bullet", f"{p['name']}: {r.choice(['farm capacity tight', 'waiting on client CAD', 'one artist out sick', 'feedback late', 'budget at 90%', 'scope creep on variants'])}"))
    blocks.append(("h2", "Numbers"))
    blocks.append(("bullet", f"Farm hours: {r.randint(800, 6400)} · Utilisation: {r.randint(62, 97)}% · Deliveries: {r.randint(1, 14)}"))
    blocks.append(("h2", "Shout-outs"))
    s = w.staff(week_start)
    blocks.append(("p", f"Thanks to {r.choice(s)['name']} for {r.choice(['jumping on the late client change', 'the new validation tool', 'mentoring the new hires', 'a heroic render weekend', 'cleaning up the asset library'])}."))
    return {"title": f"Studio weekly update: {fmt(week_start)}", "date": week_start, "author": author,
            "blocks": blocks, "active": len(live)}


def okrs(w, year, q):
    r = rng("okr", year, q)
    objs_ = r.sample([
        "Shorten review cycles", "Grow automotive revenue", "Make the asset library reusable",
        "Cut render cost per frame", "Raise client satisfaction", "Standardise the CAD intake",
        "Automate month-end close", "Ship real-time configurators", "Build a stronger bench of senior artists",
        "Make every review recording searchable"], 3)
    out = []
    for k, o in enumerate(objs_):
        krs = [(f"{r.choice(['Reduce', 'Increase', 'Reach', 'Hold'])} {m}", r.randint(40, 115))
               for m in r.sample(["average review turnaround to 2 days", "library reuse to 35% of shots",
                                  "farm cost per frame by 20%", "NPS to 60+", "on-time delivery to 92%",
                                  "automated QA coverage to 80%", "close time to 5 working days",
                                  "billable utilisation to 78%", "transcript search coverage to 100%"], 3)]
        owner = r.choice(w.staff(dt.date(year, 3 * q - 2, 1), "Leadership") or w.people[:3])["name"]
        blocks = [("h3", "Key results")] + [("bullet", f"{kr}: {pct}% of target") for kr, pct in krs] + [
            ("h3", "Retro"), ("p", r.choice(["Strong quarter, carry the momentum.", "Missed on two KRs because of hiring.",
                                             "Most of the gain came from pipeline automation.", "Client mix shifted; rebalance next quarter."]))]
        out.append({"title": f"{year} Q{q}: {o}", "owner": owner, "quarter": f"{year} Q{q}",
                    "score": round(sum(p for _, p in krs) / 300, 2), "blocks": blocks, "k": k})
    return out


def finance_month(w, y, m):
    r = rng("fin", y, m)
    live = [p for p in w.projects if p["start"] <= dt.date(y, m, 28) and p["end"] >= dt.date(y, m, 1)]
    cats = {"Software & subscriptions": r.randint(6, 22), "Render farm & cloud": r.randint(8, 60),
            "Contractors": r.randint(5, 80), "Travel": r.randint(0, 18), "Hardware": r.randint(0, 40),
            "Meals & team": r.randint(1, 6)}
    cats = {k: v * 1000 + r.randint(0, 999) for k, v in cats.items()}
    total = sum(cats.values())
    budget = int(total * r.uniform(.9, 1.15))
    blocks = [("callout", f"Brex card and bill spend for {dt.date(y, m, 1):%B %Y}, reconciled by finance"),
              ("h3", "By category")] + [("bullet", f"{k}: ${v:,}") for k, v in cats.items()] + [
              ("h3", "Notes"), ("p", r.choice(["Receipts 100% matched.", "Three receipts chased; all matched by day 4.",
                                              "Farm spend spiked for the launch film.", "Annual software renewals landed this month."]))]
    return {"title": f"Spend review: {dt.date(y, m, 1):%B %Y}", "month": dt.date(y, m, 1), "total": total,
            "budget": budget, "active": len(live), "cats": cats, "blocks": blocks}


WIKI = {
    "Studio handbook": ["How we work", "Core hours and async etiquette", "Review culture", "Holidays and leave"],
    "Naming standard (HVS-NAMING-04)": ["Projects", "Assets", "Versions", "Exports"],
    "3D pipeline SOP": ["Intake", "Modelling", "UV and texturing", "Lookdev", "Publishing"],
    "CAD intake SOP": ["Accepted formats", "Units and tolerances", "Cleanup", "Conversion to mesh"],
    "Render farm guide": ["Pools", "Priorities", "Cost tracking", "Troubleshooting"],
    "Brand & Adobe file standards": ["Illustrator", "InDesign", "Photoshop", "After Effects"],
    "Client review process": ["Rounds", "Markup tools", "Recording calls", "Sign-off"],
    "Finance: Brex card policy": ["Who gets a card", "Limits", "Receipts", "Month-end"],
    "Onboarding checklist": ["Week 1", "Week 2", "First project", "30-60-90"],
    "Asset Library map": ["01 3D Models", "02 CAD Drawings", "03 Images", "04 Spreadsheets", "05 Brex",
                          "06 Zoom Calls", "07 Adobe Creative Files", "08 Documents"],
}


def wiki(title, sections):
    r = rng("wiki", title)
    blocks = [("callout", f"{STUDIO} internal wiki · owned by Production · reviewed quarterly")]
    for s in sections:
        blocks.append(("h2", s))
        for _ in range(r.randint(2, 4)):
            blocks.append(("bullet", r.choice([
                f"{s}: always check the latest version on the project page before you start.",
                f"Ask in #studio-{r.choice(['3d', 'cad', 'design', 'pipeline', 'production'])} if anything here is unclear.",
                "Changes to this page go through a short review by the owning lead.",
                "Keep source files and exports together in the matching Asset Library folder.",
                "Record client reviews (with consent) so decisions are traceable.",
                "Version numbers only go up; never overwrite a delivered version.",
                f"{s} questions are answered within one working day.",
                "Every task links to its project and carries an assignee and a reviewer."])))
    return blocks
