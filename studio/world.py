"""Deterministic fictional studio: people, clients, projects and their 2020 -> today history.

Halcyon Vertex Studio is an invented visualisation and digital-asset studio whose work produces the
same kinds of files the Asset Library holds: 3D models, CAD drawings, building and car imagery, Adobe
creative files, spreadsheets, Brex spend data, Zoom review recordings and technical documents.
Everything is seeded, so a rerun regenerates byte-identical content and a resumed build stays consistent.
"""
import datetime as dt
import random

STUDIO = "Halcyon Vertex Studio"
START = dt.date(2020, 1, 6)
TODAY = dt.date.today()

FIRST = ["Maya", "Daniel", "Priya", "Marcus", "Elena", "Kenji", "Olivia", "Rahul", "Sofia", "Ethan", "Amara",
         "Lucas", "Hannah", "Wei", "Isabel", "Noah", "Zara", "Gabriel", "Chloe", "Arjun", "Leah", "Mateo",
         "Grace", "Tobias", "Nadia", "Owen", "Mei", "Julian", "Aisha", "Connor", "Valeria", "Samuel", "Ivy",
         "Rohan", "Camille", "Felix", "Anika", "Diego", "Freya", "Hiro", "Lena", "Victor", "Ruth", "Sanjay",
         "Tessa", "Adrian", "Yuki", "Brooke", "Emeka", "Clara", "Jonah", "Lila", "Marco", "Esther", "Kai",
         "Paige", "Andre", "Nina"]
LAST = ["Chen", "Okafor", "Raman", "Whitfield", "Novak", "Tanaka", "Brennan", "Mehta", "Alvarez", "Caldwell",
        "Osei", "Fischer", "Park", "Zhang", "Moreau", "Lindqvist", "Haddad", "Santos", "Dubois", "Iyer",
        "Kowalski", "Reyes", "Holloway", "Becker", "Farouk", "Gallagher", "Liu", "Ashford", "Bello", "Murphy",
        "Castillo", "Adeyemi", "Sinclair", "Kapoor", "Laurent", "Hartmann", "Desai", "Romero", "Nilsson",
        "Sato", "Vogel", "Marchetti", "Abrams", "Pillai", "Quinn", "Delgado", "Mori", "Sterling", "Nwosu",
        "Ellison", "Kerr", "Banerjee", "Rossi", "Feld", "Kahale", "Morrow", "Baptiste", "Petrova"]

ROLES = [  # department, role, how many over the history
    ("Leadership", "Founder & Creative Director", 1), ("Leadership", "Chief Operating Officer", 1),
    ("Leadership", "Head of Production", 1), ("Leadership", "Technical Director", 1),
    ("3D", "Lead 3D Artist", 2), ("3D", "Senior 3D Artist", 5), ("3D", "3D Artist", 7),
    ("3D", "Technical Artist", 3), ("3D", "Lighting & Lookdev Artist", 2),
    ("CAD & BIM", "BIM Coordinator", 2), ("CAD & BIM", "CAD Technician", 4),
    ("Design", "Art Director", 2), ("Design", "Graphic Designer", 3), ("Design", "Motion Designer", 3),
    ("Pipeline", "Pipeline TD", 3), ("Pipeline", "Software Engineer", 3), ("Pipeline", "Render Wrangler", 2),
    ("Production", "Producer", 3), ("Production", "Project Manager", 3),
    ("Client Services", "Account Director", 2), ("Finance & Ops", "Finance Manager", 1),
    ("Finance & Ops", "Operations Coordinator", 2),
]
OFFICES = ["Austin, TX", "Toronto, ON", "Denver, CO", "Vancouver, BC", "Remote (Portland, OR)",
           "Remote (Chicago, IL)", "Remote (Atlanta, GA)", "Remote (Montreal, QC)"]

CLIENT_A = ["Northgate", "Ashbury", "Corvane", "Meridian", "Stoneleigh", "Halvorsen", "Bayline", "Tamsin",
            "Ridgeway", "Kestrel", "Pinecrest", "Larkspur", "Vantor", "Oakhaven", "Silverline", "Crestmark",
            "Weston", "Aurelia", "Brookfield", "Calder", "Driftway", "Emberly", "Foxhollow", "Granwick",
            "Harrowgate", "Ironvale", "Juniper", "Kingsley", "Lumen", "Marlowe", "Newhaven", "Orchard"]
CLIENT_KIND = [  # suffix, industry, what they buy
    ("Architects", "Architecture", "arch"), ("Development Group", "Real estate", "arch"),
    ("Motors", "Automotive", "auto"), ("Automotive Design", "Automotive", "auto"),
    ("Interactive", "Games & XR", "asset"), ("Manufacturing", "Industrial", "cad"),
    ("Engineering", "Engineering", "cad"), ("Creative Agency", "Marketing", "brand"),
    ("Homes", "Residential construction", "arch"), ("Mobility", "Automotive", "auto"),
    ("Retail Group", "Retail", "brand"), ("City Planning Office", "Public sector", "arch"),
]

KINDS = {
    "arch": {"label": "Architectural visualisation", "folders": ["01 3D Models/FBX", "02 CAD Drawings/DXF",
             "03 Images/Buildings & Architecture", "07 Adobe Creative Files/Photoshop (PSD)"],
             "names": ["{c} Tower Renders", "{c} Civic Centre Visualisation", "{c} Waterfront Masterplan",
                       "{c} Residential Phase {n} Walkthrough", "{c} Campus BIM-to-Render", "{c} Lobby Lookdev",
                       "{c} Mixed-Use Block Aerials", "{c} Transit Hub Concept Pack"]},
    "auto": {"label": "Automotive visualisation", "folders": ["01 3D Models/BLEND", "01 3D Models/GLB",
             "03 Images/Cars", "07 Adobe Creative Files/After Effects (AEP)"],
             "names": ["{c} EV Configurator Assets", "{c} Coupe Launch Renders", "{c} Interior Trim Library",
                       "{c} Showroom Turntables", "{c} Concept Car Reveal Film", "{c} Wheel & Paint Variants",
                       "{c} Dealer Marketing Kit {n}"]},
    "asset": {"label": "3D asset library", "folders": ["01 3D Models/GLB", "01 3D Models/OBJ",
              "01 3D Models/STL", "01 3D Models/USDZ"],
              "names": ["{c} Environment Prop Pack {n}", "{c} Character Kitbash Library", "{c} XR Asset Optimisation",
                        "{c} Photogrammetry Cleanup", "{c} Modular City Kit", "{c} Vehicle Asset Pack"]},
    "cad": {"label": "CAD conversion & digitisation", "folders": ["02 CAD Drawings/STEP", "02 CAD Drawings/IGES",
            "02 CAD Drawings/FreeCAD", "01 3D Models/STL"],
            "names": ["{c} Factory Layout Digitisation", "{c} STEP-to-Mesh Conversion", "{c} Legacy Drawing Archive",
                      "{c} Assembly Exploded Views", "{c} Plant Retrofit Models", "{c} Parts Catalogue Renders"]},
    "brand": {"label": "Brand & motion design", "folders": ["07 Adobe Creative Files/Illustrator (AI)",
              "07 Adobe Creative Files/InDesign (INDD, IDML)", "07 Adobe Creative Files/After Effects (AEP)",
              "03 Images/PNG"],
              "names": ["{c} Brand Refresh", "{c} Motion Graphics Package", "{c} Campaign Key Visuals {n}",
                        "{c} Store Launch Collateral", "{c} Product Explainer Animation"]},
}
INTERNAL = [  # studio's own projects: tooling, data, finance, archives
    ("Core Asset Library v{n}", "asset", ["01 3D Models/GLB", "01 3D Models/FBX", "04 Spreadsheets/XLSX"]),
    ("Render Farm Cost Model", "data", ["04 Spreadsheets/XLSX", "04 Spreadsheets/CSV"]),
    ("Asset Metadata Catalogue", "data", ["04 Spreadsheets/CSV", "08 Documents/PDF"]),
    ("Brex Spend Controls Rollout", "finance", ["05 Brex/Company Datasets", "04 Spreadsheets/XLSX"]),
    ("Quarterly Close Automation", "finance", ["05 Brex/Company Datasets", "04 Spreadsheets/XLSX"]),
    ("Client Review Recording Archive", "zoom", ["06 Zoom Calls/Generated Calls", "06 Zoom Calls/Public Meetings"]),
    ("Standards & Reference Library", "docs", ["08 Documents/PDF", "08 Documents/TXT"]),
    ("Pipeline Automation {n}", "pipeline", ["01 3D Models/GLB", "02 CAD Drawings/STEP"]),
    ("Brush & Texture Library", "brand", ["07 Adobe Creative Files/Photoshop Brushes (ABR)",
                                         "07 Adobe Creative Files/Photoshop (PSD)"]),
]
DEPT_FOR = {"arch": ["3D", "CAD & BIM", "Design"], "auto": ["3D", "Design"], "asset": ["3D", "Pipeline"],
            "cad": ["CAD & BIM", "3D"], "brand": ["Design"], "data": ["Pipeline", "Finance & Ops"],
            "finance": ["Finance & Ops"], "zoom": ["Production", "Pipeline"], "docs": ["Production", "CAD & BIM"],
            "pipeline": ["Pipeline", "3D"]}


def d(x):
    return x.isoformat()


def months_between(a, b):
    return (b.year - a.year) * 12 + b.month - a.month


class World:
    def __init__(self, seed=2020):
        self.r = random.Random(seed)
        self.people = self._people()
        self.clients = self._clients()
        self.projects = self._projects()
        self.sprints = self._sprints()

    # ---- people ------------------------------------------------------------------------------------------
    def _people(self):
        r = self.r
        names = set()
        out = []
        for dept, role, n in ROLES:
            for k in range(n):
                while True:
                    nm = f"{r.choice(FIRST)} {r.choice(LAST)}"
                    if nm not in names:
                        names.add(nm)
                        break
                if dept == "Leadership" or (k == 0 and n > 1):
                    start = dt.date(2019, r.randint(3, 12), r.randint(1, 28))
                else:
                    start = START + dt.timedelta(days=r.randint(0, (TODAY - START).days - 120))
                end = None
                if dept != "Leadership" and r.random() < .22:
                    e = start + dt.timedelta(days=r.randint(300, 1300))
                    end = e if e < TODAY - dt.timedelta(days=30) else None
                out.append({"name": nm, "dept": dept, "role": role, "office": r.choice(OFFICES),
                            "start": start, "end": end})
        out.sort(key=lambda p: p["start"])
        return out

    def staff(self, on, dept=None):
        return [p for p in self.people if p["start"] <= on and (p["end"] is None or p["end"] > on)
                and (dept is None or p["dept"] == dept)]

    # ---- clients -----------------------------------------------------------------------------------------
    def _clients(self):
        r = self.r
        out = []
        for i, a in enumerate(r.sample(CLIENT_A, 30)):
            suf, ind, kind = CLIENT_KIND[i % len(CLIENT_KIND)]
            out.append({"name": f"{a} {suf}", "short": a, "industry": ind, "kind": kind,
                        "city": r.choice(["Austin", "Dallas", "Toronto", "Seattle", "Denver", "Chicago",
                                          "Vancouver", "Detroit", "Atlanta", "Phoenix", "Boston", "Calgary",
                                          "San Diego", "Minneapolis", "Ottawa", "Nashville"]),
                        "since": START + dt.timedelta(days=r.randint(0, 1900))})
        out.sort(key=lambda c: c["since"])
        return out

    # ---- projects ----------------------------------------------------------------------------------------
    def _projects(self):
        r = self.r
        out = []
        used = set()
        seq = 0

        def add(name, kind, folders, client, start):
            nonlocal seq
            seq += 1
            months = r.choice([2, 3, 3, 4, 5, 6, 6, 8, 10, 12]) if kind not in ("finance", "docs") else r.randint(3, 9)
            end = start + dt.timedelta(days=months * 30 + r.randint(-10, 20))
            lead_pool = [p for p in self.staff(start) if p["dept"] in DEPT_FOR.get(kind, ["3D"])
                         and ("Lead" in p["role"] or "Senior" in p["role"] or "Director" in p["role"]
                              or p["role"] in ("BIM Coordinator", "Pipeline TD", "Finance Manager", "Producer"))]
            lead_pool = lead_pool or self.staff(start, "Leadership")
            lead = r.choice(lead_pool)
            prod = r.choice(self.staff(start, "Production") or self.staff(start, "Leadership"))
            pool = [p for p in self.staff(start) if p["dept"] in DEPT_FOR.get(kind, ["3D"]) + ["Pipeline"]]
            team = r.sample(pool, min(len(pool), r.randint(3, 7)))
            team = [lead, prod] + [p for p in team if p not in (lead, prod)]
            if end <= TODAY:
                status = "Delivered" if r.random() > .06 else "Cancelled"
            elif start > TODAY:
                status = "Planned"
            else:
                status = "In progress" if r.random() > .12 else "At risk"
            budget = int(r.choice([18, 24, 32, 45, 60, 85, 120, 160, 220]) * 1000 * (1 + months / 12))
            spent_ratio = r.uniform(.82, 1.18) if status == "Delivered" else (
                max(0.0, min(1.0, (TODAY - start).days / max(1, (end - start).days))) * r.uniform(.8, 1.1))
            out.append({"id": f"P{seq:03d}", "code": f"HVS-{start.year % 100:02d}{seq:03d}", "name": name,
                        "kind": kind, "label": KINDS.get(kind, {}).get("label", kind.title()),
                        "folders": folders, "client": client, "start": start, "end": end, "months": months,
                        "lead": lead["name"], "producer": prod["name"], "team": [p["name"] for p in team],
                        "status": status, "budget": budget, "spent": int(budget * spent_ratio),
                        "priority": r.choice(["P1", "P2", "P2", "P3"])})

        day = START
        while day < TODAY + dt.timedelta(days=40):
            clients = [c for c in self.clients if c["since"] <= day + dt.timedelta(days=60)] or self.clients[:3]
            if r.random() < .78:
                c = r.choice(clients)
                spec = KINDS[c["kind"]]
                for _ in range(10):
                    nm = r.choice(spec["names"]).format(c=c["short"], n=r.randint(1, 4))
                    if nm not in used:
                        break
                used.add(nm)
                add(nm, c["kind"], spec["folders"], c["name"], day)
            else:
                nm, kind, folders = r.choice(INTERNAL)
                nm = nm.format(n=sum(1 for p in out if p["kind"] == kind) + 1)
                if nm in used:
                    nm += f" ({day.year})"
                used.add(nm)
                add(nm, kind, folders, None, day)
            day += dt.timedelta(days=r.randint(22, 45))
        return out

    def _sprints(self):
        out = []
        s = START
        n = 1
        while s <= TODAY:
            out.append({"name": f"Sprint {n:03d}", "start": s, "end": s + dt.timedelta(days=13), "n": n})
            s += dt.timedelta(days=14)
            n += 1
        return out

    def sprint_for(self, day):
        i = max(0, min(len(self.sprints) - 1, (day - START).days // 14))
        return self.sprints[i]["name"]
