"""The ~120-page section tree under Studio Workspace: 12 section pages x 9 pages each. Pages that hold a
database name it in DB; every other page gets generated prose, tables and a dated collaboration log."""
import datetime as dt

from .content import between, clamp, fmt, rng
from .world import STUDIO, START, TODAY

# section title, emoji, intro, [(page title, emoji, database key or None, departments that own it)]
SECTIONS = [
    ("Company & Team", "🏢", "Who we are, how we are organised and how people join and grow.", [
        ("About the studio", "✨", None, ["Leadership"]), ("Org chart", "🧭", None, ["Leadership"]),
        ("Team directory", "👥", "people", ["Finance & Ops"]), ("Hiring & onboarding", "🤝", None, ["Finance & Ops"]),
        ("Offices & remote work", "🗺️", None, ["Finance & Ops"]), ("Values & culture", "💡", None, ["Leadership"]),
        ("Leadership updates", "📣", None, ["Leadership"]), ("Performance & growth", "📈", None, ["Leadership"]),
        ("Holidays & studio calendar", "📅", None, ["Finance & Ops"])]),
    ("Clients & Accounts", "🤝", "Every client relationship from first pitch to renewal.", [
        ("Client list", "📇", "clients", ["Client Services"]), ("Account plans", "🎯", None, ["Client Services"]),
        ("Proposals & pitches", "📝", None, ["Client Services"]), ("Contracts & SOWs", "📜", None, ["Production"]),
        ("Client feedback log", "💬", None, ["Client Services"]), ("Renewals & upsell", "🔁", None, ["Client Services"]),
        ("Client onboarding", "🚪", None, ["Production"]), ("Case studies", "🏆", None, ["Design"]),
        ("Relationship notes", "🗒️", None, ["Client Services"])]),
    ("Projects", "🚀", "The project portfolio, the work breakdown and how delivery is planned.", [
        ("Project portfolio", "📁", "projects", ["Production"]), ("Tasks", "✅", "tasks", ["Production"]),
        ("Sprints", "🏃", "sprints", ["Production"]), ("Roadmap 2020-2026", "🛣️", None, ["Leadership"]),
        ("Project templates", "🧩", None, ["Production"]), ("Change requests", "🔀", None, ["Production"]),
        ("Risk register", "⚠️", None, ["Production"]), ("Milestones", "🏁", None, ["Production"]),
        ("Postmortems", "🔍", None, ["Production"])]),
    ("Production & Pipeline", "⚙️", "Tools, automation and the render farm that move work from intake to delivery.", [
        ("Pipeline overview", "🧪", None, ["Pipeline"]), ("Render farm guide", "🖥️", None, ["Pipeline"]),
        ("Publish tool", "📤", None, ["Pipeline"]), ("Validation checks", "🛡️", None, ["Pipeline"]),
        ("Naming standard", "🏷️", None, ["Pipeline"]), ("Tool requests", "🧰", None, ["Pipeline"]),
        ("Automation backlog", "🤖", None, ["Pipeline"]), ("Pipeline releases", "📦", None, ["Pipeline"]),
        ("Incident log", "🚨", None, ["Pipeline"])]),
    ("3D Models", "🧊", "Modelling standards and the shared model library (FBX, OBJ, GLB, BLEND, STL, USDZ ...).", [
        ("3D modelling SOP", "📐", None, ["3D"]), ("Polycount budgets", "🔺", None, ["3D"]),
        ("Format guide", "🗂️", None, ["3D"]), ("Materials & textures", "🎨", None, ["3D"]),
        ("LOD guidelines", "🪜", None, ["3D"]), ("Model review checklist", "☑️", None, ["3D"]),
        ("Photogrammetry", "📷", None, ["3D"]), ("Asset register", "🗃️", "assets", ["Pipeline"]),
        ("Technical art notes", "🔧", None, ["3D"])]),
    ("CAD & BIM", "📏", "Intake, conversion and coordination of client CAD (STEP, IGES, DXF, FreeCAD).", [
        ("CAD intake SOP", "📥", None, ["CAD & BIM"]), ("Units & tolerances", "📏", None, ["CAD & BIM"]),
        ("STEP & IGES conversion", "🔄", None, ["CAD & BIM"]), ("DXF layer standard", "🧱", None, ["CAD & BIM"]),
        ("BIM coordination", "🏗️", None, ["CAD & BIM"]), ("Parametric parts (FreeCAD)", "⚙️", None, ["CAD & BIM"]),
        ("Drawing archive", "🗄️", None, ["CAD & BIM"]), ("CAD QA checklist", "✔️", None, ["CAD & BIM"]),
        ("Client CAD issues", "🐞", None, ["CAD & BIM"])]),
    ("Images & Visualisation", "🖼️", "How we light, frame and finish building and car imagery.", [
        ("Arch-viz style guide", "🏙️", None, ["3D"]), ("Automotive style guide", "🚗", None, ["3D"]),
        ("Lighting & HDRI library", "💡", None, ["3D"]), ("Camera presets", "🎥", None, ["3D"]),
        ("Image formats & colour", "🌈", None, ["Design"]), ("Retouching guide", "🖌️", None, ["Design"]),
        ("Reference boards", "📌", None, ["Design"]), ("Render reviews", "👀", None, ["3D"]),
        ("Portfolio selects", "⭐", None, ["Design"])]),
    ("Adobe Creative", "🎨", "Brand, layout and motion work in Illustrator, InDesign, Photoshop, After Effects and XD.", [
        ("Brand standards", "🔤", None, ["Design"]), ("Illustrator", "✒️", None, ["Design"]),
        ("InDesign", "📰", None, ["Design"]), ("Photoshop", "🖼️", None, ["Design"]),
        ("After Effects", "🎞️", None, ["Design"]), ("XD prototypes", "📱", None, ["Design"]),
        ("Brush & texture library", "🖍️", None, ["Design"]), ("Fonts & type", "🔠", None, ["Design"]),
        ("Creative reviews", "🧑‍🎨", None, ["Design"])]),
    ("Data & Spreadsheets", "📊", "Studio data: metadata, cost models and the spreadsheets that run the business.", [
        ("Asset metadata catalogue", "🧾", None, ["Pipeline"]), ("Render cost model", "💰", None, ["Pipeline"]),
        ("Utilisation dashboards", "📈", None, ["Production"]), ("Storage forecast", "💾", None, ["Pipeline"]),
        ("Data dictionary", "📖", None, ["Pipeline"]), ("CSV export jobs", "🔁", None, ["Pipeline"]),
        ("Reporting calendar", "🗓️", None, ["Finance & Ops"]), ("KPI definitions", "🎯", None, ["Leadership"]),
        ("Spreadsheet templates", "📑", None, ["Finance & Ops"])]),
    ("Finance & Brex", "💳", "Cards, spend, budgets and month-end close, run on Brex.", [
        ("Brex card policy", "💳", None, ["Finance & Ops"]), ("Monthly spend reviews", "🧮", "finance", ["Finance & Ops"]),
        ("Project budgets", "📒", None, ["Finance & Ops"]), ("Month-end close", "📆", None, ["Finance & Ops"]),
        ("Vendors", "🏪", None, ["Finance & Ops"]), ("Expense categories & GL", "🗂️", None, ["Finance & Ops"]),
        ("Audit trail", "🔎", None, ["Finance & Ops"]), ("Forecasts", "🔮", None, ["Finance & Ops"]),
        ("Invoicing", "🧾", None, ["Finance & Ops"])]),
    ("Meetings & Zoom", "🎙️", "Meeting notes, weekly updates and the archive of recorded client reviews.", [
        ("Meeting notes", "🗒️", "meetings", ["Production"]), ("Weekly updates", "📰", "weekly", ["Production"]),
        ("All-hands", "🙌", None, ["Leadership"]), ("Client review recordings", "📹", None, ["Production"]),
        ("Retrospectives", "🔄", None, ["Production"]), ("Meeting norms", "🤫", None, ["Leadership"]),
        ("Zoom recording policy", "🎬", None, ["Finance & Ops"]), ("Transcript archive", "📜", None, ["Pipeline"]),
        ("Rituals calendar", "🗓️", None, ["Production"])]),
    ("Knowledge & Documents", "📚", "Specs, decisions, goals and the studio's reference library.", [
        ("Docs & specs", "📄", "docs", ["Production"]), ("Decision log", "⚖️", "decisions", ["Leadership"]),
        ("OKRs", "🎯", "okrs", ["Leadership"]), ("Wiki home", "🏠", None, ["Production"]),
        ("Standards library", "📚", None, ["CAD & BIM"]), ("Glossary", "🔤", None, ["Production"]),
        ("Research notes", "🔬", None, ["Pipeline"]), ("Templates", "🧩", None, ["Production"]),
        ("Reading list", "📖", None, ["Leadership"])]),
]

POINTS = [
    "{t}: the current version is the source of truth; older guidance is kept in the change history below.",
    "Owners review {t} every quarter and after any incident that touches it.",
    "Ask in #studio-{ch} if something in {t} doesn't match what you see on a project.",
    "New starters read {t} in their first two weeks; leads walk them through it on a real ticket.",
    "Every change to {t} gets a one-line entry in the log with who, when and why.",
    "{t} applies to client and internal projects alike; exceptions are agreed with the project lead.",
    "Link {t} from the project page whenever a ticket depends on it.",
    "Files that {t} refers to live in the matching Asset Library folder, never on personal drives.",
    "When {t} and a client contract disagree, the contract wins and we note the exception here.",
    "Metrics for {t} are reported in the studio weekly update.",
]
CHANGES = [
    "Rewrote the intro for clarity after onboarding feedback.", "Added a worked example from a recent project.",
    "Removed an outdated step that the publish tool now does automatically.",
    "Merged duplicate guidance from the old wiki.", "Updated screenshots for the new tool version.",
    "Clarified who signs off and when.", "Added the client-facing version of this section.",
    "Linked the new checklist and template.", "Reorganised sections to match the pipeline order.",
    "Captured decisions from the last retro.", "Fixed broken links after the Drive reorganisation.",
    "Added numbers from the latest quarter.",
]
TALK = [
    "Should this cover the {x} case too? We hit it twice last month.",
    "Agreed. I'll add a short example and tag {n} to review.",
    "This saved me an hour on the last delivery. Thanks for writing it up.",
    "Small correction: the threshold is now {k}, not {k2}. Updated.",
    "Can we link this from the onboarding checklist?",
    "Reviewed. Looks right to me, approving the change.",
    "We should revisit this after the next big project wraps.",
    "Adding the client-facing wording here so account leads can reuse it.",
    "I moved the old version to the archive section so history isn't lost.",
    "Flagging for the quarterly review: two teams interpret this differently.",
]


def page_blocks(w, sec, title, owners):
    """Generic section page: intro, principles, a fact table, a change log and a discussion spanning years."""
    r = rng("section", sec, title)
    staff = [p for p in w.people if p["dept"] in owners] or w.people
    owner = r.choice(staff)
    created = between(r, START, dt.date(2022, 6, 1))
    ch = r.choice(["3d", "cad", "design", "pipeline", "production", "finance", "general"])
    b = [("callout", f"Owner: {owner['name']} ({owner['role']}) · Created {fmt(created)} · Section: {sec}"),
         ("p", f"This page is part of the {STUDIO} workspace. It explains {title.lower()} and records how "
               f"that practice has changed since {created.year}.")]
    b.append(("h2", "Key points"))
    for s in r.sample(POINTS, 5):
        b.append(("bullet", s.format(t=title, ch=ch)))
    b.append(("h2", "At a glance"))
    rows = [["Item", "Value", "Owner", "Last checked"]]
    for k in range(r.randint(4, 7)):
        rows.append([r.choice(["Scope", "Applies to", "Review cadence", "Escalation", "Tooling", "Metric",
                               "Target", "Exceptions", "Related SOP", "Storage"]) + f" {k + 1}",
                     r.choice(["All projects", "Quarterly", "Monthly", "Client work only", "Asset Library",
                               "Brex", "Render farm", "Production leads", "≤ 2 working days", "95%+"]),
                     r.choice(staff)["name"], fmt(clamp(between(r, created, TODAY)))])
    b.append(("table", rows))
    b.append(("h2", "Change history"))
    day = created
    while day < TODAY:
        who = r.choice([p for p in w.people if p["start"] <= day] or w.people)
        b.append(("bullet_rich", f"{fmt(day)} · {who['name']}", r.choice(CHANGES)))
        day += dt.timedelta(days=r.randint(60, 200))
    b.append(("h2", "Discussion"))
    day = created
    for _ in range(r.randint(5, 10)):
        day = clamp(day + dt.timedelta(days=r.randint(20, 160)))
        who = r.choice([p for p in w.people if p["start"] <= day and (p["end"] is None or p["end"] > day)] or w.people)
        b.append(("msg", who["name"], day, r.choice(TALK).format(
            x=r.choice(["rush delivery", "client-supplied CAD", "outsourced asset", "late feedback", "4K print"]),
            n=r.choice(staff)["name"].split()[0], k=r.randint(3, 9), k2=r.randint(10, 20))))
    return b[:100]


def special_blocks(w, title):
    """Pages that draw on the world data directly (org chart, roadmap, budgets ...)."""
    if title == "Org chart":
        b = [("p", "Current reporting lines, by department. People who have left are listed in the Team directory.")]
        depts = {}
        for p in w.staff(TODAY):
            depts.setdefault(p["dept"], []).append(p)
        for dep, ps in depts.items():
            b.append(("h3", dep))
            b += [("bullet", f"{p['name']}: {p['role']} ({p['office']}, since {p['start'].year})") for p in ps][:20]
        return b[:100]
    if title == "Roadmap 2020-2026":
        b = [("p", "Every project the studio has run or planned, by year.")]
        for y in range(2020, TODAY.year + 1):
            ps = [p for p in w.projects if p["start"].year == y]
            b.append(("h3", f"{y} ({len(ps)} projects)"))
            b += [("bullet", f"{p['code']} {p['name']}: {p['status']}, {fmt(p['start'])} to {fmt(p['end'])}, lead {p['lead']}")
                  for p in ps][:12]
        return b[:100]
    if title == "Project budgets":
        rows = [["Code", "Project", "Budget", "Spent", "Status"]] + [
            [p["code"], p["name"], f"${p['budget']:,}", f"${p['spent']:,}", p["status"]] for p in w.projects[-60:]]
        return [("p", "Budgets and spend to date for the most recent projects (full list in Project portfolio)."),
                ("table", rows[:60])]
    if title == "Milestones":
        b = [("p", "Key milestones across the portfolio.")]
        for p in w.projects[-40:]:
            b.append(("bullet", f"{p['code']} {p['name']}: kickoff {fmt(p['start'])}, final delivery {fmt(p['end'])}"))
        return b
    return None
