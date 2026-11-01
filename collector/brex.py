"""Brex: the public developer reference (OpenAPI specifications, guides, examples) and 150 company datasets in
Brex API formats for fictional companies (users, departments, locations, cards, card and cash transactions,
statements, expenses with receipts, budgets, spend limits, vendors, transfers, trips and bookings), as JSON
exactly as the API returns it, plus CSV and XLSX exports. Field names and enum values come from the specs."""
import csv
import io
import json
import random
import uuid
from datetime import date, datetime, timedelta, timezone

import yaml

from .common import add_sheet, get, new_book, safe, save_book, session
from .util import BREX

DEV = "https://developer.brex.com"
APIS = ["accounting", "budgets", "expenses", "fields", "onboarding", "payments", "team", "transactions",
        "travel", "webhooks"]
COMPANIES = 150


def _enum(specs, api, name):
    return specs[api]["components"]["schemas"][name]["enum"]


def reference(sink, st):
    """API specifications (YAML), an endpoint catalogue (XLSX) and every guide and example page (Markdown)."""
    if st.get("brex_ref"):
        return 0
    s = session()
    n = 0
    rows = []
    for a in APIS:
        r = get(s, f"{DEV}/_spec/openapi/{a}_api.yaml")
        if not r:
            continue
        sink.write_text(f"{BREX}/Developer Reference/API Specifications/{a}_api.yaml", r.text)
        n += 1
        spec = yaml.safe_load(r.text)
        for path, ops in (spec.get("paths") or {}).items():
            for method, op in ops.items():
                if isinstance(op, dict) and method in ("get", "post", "put", "delete", "patch"):
                    scopes = sorted({x for sec in op.get("security") or [] for v in sec.values() for x in v})
                    rows.append([spec["info"]["title"], method.upper(), path, op.get("summary", ""),
                                 op.get("operationId", ""), ", ".join(scopes)])
    wb = new_book()
    add_sheet(wb, "Endpoints", ["API", "Method", "Path", "Summary", "Operation ID", "OAuth scopes"], rows,
              {"Path": 50, "Summary": 60, "OAuth scopes": 40})
    save_book(sink, f"{BREX}/Developer Reference/Brex API endpoints.xlsx", wb)
    idx = get(s, f"{DEV}/llms.txt")
    for line in (idx.text.splitlines() if idx else []):
        if "](" not in line:
            continue
        title, url = line.split("[", 1)[1].split("](", 1)
        url = url.rstrip(")")
        if not url.endswith(".md") or "/openapi/" in url:
            continue
        r = get(s, url)
        if r and r.text.strip():
            section = url.replace(DEV + "/", "").split("/")[0].replace(".md", "")
            folder = {"docs": "Guides", "guides": "Guides", "examples": "Examples", "onboarding": "Guides"}.get(
                section, "Guides")
            sink.write_text(f"{BREX}/Developer Reference/{folder}/{safe(title, 80)}.md", r.text)
            n += 1
    st["brex_ref"] = True
    return n


# ---- fictional companies -------------------------------------------------------------------------------
NAME_A = ["Alder", "Bramble", "Cinder", "Driftwood", "Ember", "Fernhill", "Granite", "Harbor", "Ironleaf", "Juniper",
          "Kestrel", "Lantern", "Meridian", "Northgate", "Oakmont", "Pinecrest", "Quillon", "Redwood", "Saltmarsh",
          "Tidewater", "Umber", "Vantage", "Willow", "Yarrow", "Zephyr", "Copperline", "Bluefield", "Stonebridge",
          "Silverpeak", "Larkspur"]
NAME_B = ["Labs", "Analytics", "Health", "Robotics", "Logistics", "Studios", "Systems", "Foods", "Energy", "Bio",
          "Security", "Commerce", "Learning", "Mobility", "Finance", "Networks", "Devices", "Media", "Cloud", "Works"]
INDUSTRY = {"Labs": "Software", "Analytics": "Software", "Health": "Healthcare", "Robotics": "Hardware",
            "Logistics": "Logistics", "Studios": "Media", "Systems": "Software", "Foods": "Consumer goods",
            "Energy": "Energy", "Bio": "Biotech", "Security": "Software", "Commerce": "E-commerce",
            "Learning": "Education", "Mobility": "Transportation", "Finance": "Fintech", "Networks": "Telecom",
            "Devices": "Hardware", "Media": "Media", "Cloud": "Software", "Works": "Professional services"}
FIRST = ["Avery", "Blake", "Casey", "Dana", "Elliot", "Finley", "Gray", "Harper", "Indy", "Jordan", "Kai", "Logan",
         "Morgan", "Noel", "Oakley", "Parker", "Quinn", "Reese", "Sage", "Taylor", "Umi", "Val", "Wren", "Xen",
         "Yael", "Zion", "Amara", "Bodhi", "Cyrus", "Delphine", "Emeka", "Farah", "Goran", "Hana", "Ines", "Jae",
         "Kofi", "Leilani", "Mateo", "Nadia", "Omar", "Priya", "Ravi", "Sofia", "Tomas", "Uma", "Vikram", "Yuki"]
LAST = ["Abernathy", "Brightwater", "Castellan", "Dunmore", "Ellery", "Fairbanks", "Galloway", "Hartwell", "Ingram",
        "Jessup", "Kingsley", "Lockhart", "Marlowe", "Nightingale", "Okafor", "Pemberton", "Quintero", "Rowntree",
        "Sandoval", "Thorne", "Underhill", "Vasquez", "Whitlock", "Yardley", "Zamora", "Achebe", "Banerjee", "Chen",
        "Delacroix", "Esposito", "Fujimoto", "Gallagher", "Haddad", "Iverson", "Jovanovic", "Kowalski", "Lindqvist"]
DEPTS = ["Engineering", "Product", "Design", "Sales", "Marketing", "Customer Success", "Finance", "People",
         "Operations", "Legal", "IT", "Executive"]
CITIES = [("San Francisco", "CA", "94105", "America/Los_Angeles"), ("New York", "NY", "10013", "America/New_York"),
          ("Austin", "TX", "78701", "America/Chicago"), ("Seattle", "WA", "98101", "America/Los_Angeles"),
          ("Chicago", "IL", "60606", "America/Chicago"), ("Boston", "MA", "02110", "America/New_York"),
          ("Denver", "CO", "80202", "America/Denver"), ("Miami", "FL", "33131", "America/New_York"),
          ("Atlanta", "GA", "30303", "America/New_York"), ("Los Angeles", "CA", "90015", "America/Los_Angeles")]
STREETS = ["Market St", "Mission St", "Broadway", "Congress Ave", "Pine St", "Wacker Dr", "Boylston St",
           "Larimer St", "Brickell Ave", "Peachtree St", "Spring St"]

# merchant: (category, mcc, typical cents low, high, who buys: dept or "*")
MERCHANTS = {
    "AWS": ("SOFTWARE_NON_RECURRING", "4816", 40000, 2500000, "Engineering"),
    "GOOGLE*CLOUD": ("SOFTWARE_NON_RECURRING", "4816", 20000, 900000, "Engineering"),
    "GITHUB": ("SOFTWARE_NON_RECURRING", "5734", 2100, 210000, "Engineering"),
    "ATLASSIAN": ("SOFTWARE_NON_RECURRING", "5734", 8000, 300000, "Engineering"),
    "FIGMA": ("SOFTWARE_NON_RECURRING", "5734", 1500, 90000, "Design"),
    "SLACK TECHNOLOGIES": ("SOFTWARE_NON_RECURRING", "5734", 9000, 400000, "IT"),
    "ZOOM.US": ("SOFTWARE_NON_RECURRING", "4899", 1499, 60000, "IT"),
    "LINKEDIN ADS": ("ADVERTISING_AND_MARKETING", "7311", 50000, 1500000, "Marketing"),
    "GOOGLE ADS": ("ADVERTISING_AND_MARKETING", "7311", 100000, 3000000, "Marketing"),
    "META ADS": ("ADVERTISING_AND_MARKETING", "7311", 80000, 2000000, "Marketing"),
    "UNITED AIRLINES": ("AIRFARE", "3000", 18000, 140000, "*"),
    "DELTA AIR LINES": ("AIRFARE", "3058", 16000, 150000, "*"),
    "MARRIOTT": ("LODGING", "3509", 15000, 120000, "*"),
    "HILTON HOTELS": ("LODGING", "3504", 14000, 110000, "*"),
    "UBER *TRIP": ("TAXI_AND_RIDESHARE", "4121", 1200, 9000, "*"),
    "LYFT *RIDE": ("TAXI_AND_RIDESHARE", "4121", 1100, 8000, "*"),
    "HERTZ": ("CAR_RENTAL", "3357", 9000, 60000, "Sales"),
    "SWEETGREEN": ("RESTAURANTS", "5814", 1400, 9000, "*"),
    "DOORDASH": ("RESTAURANTS", "5812", 2500, 45000, "*"),
    "STARBUCKS": ("RESTAURANTS", "5814", 450, 3500, "*"),
    "THE CAPITAL GRILLE": ("RESTAURANTS", "5812", 15000, 120000, "Sales"),
    "STAPLES": ("OFFICE_SUPPLIES", "5943", 1500, 40000, "Operations"),
    "AMAZON MKTPL": ("OFFICE_SUPPLIES", "5942", 1000, 80000, "*"),
    "APPLE.COM/BILL": ("ELECTRONICS", "5732", 9900, 350000, "IT"),
    "BEST BUY": ("ELECTRONICS", "5732", 3000, 250000, "IT"),
    "FEDEX": ("SHIPPING", "4215", 1200, 30000, "Operations"),
    "UPS": ("SHIPPING", "4215", 1000, 25000, "Operations"),
    "WEWORK": ("FACILITIES_EXPENSES", "6513", 50000, 900000, "Operations"),
    "COMCAST BUSINESS": ("UTILITIES", "4900", 15000, 60000, "Operations"),
    "VERIZON WIRELESS": ("TELEPHONY", "4814", 8000, 90000, "IT"),
    "EVENTBRITE": ("EVENT_EXPENSES", "7922", 5000, 300000, "Marketing"),
    "COURSERA": ("EDUCATION", "8299", 3900, 40000, "People"),
    "DOCUSIGN": ("SOFTWARE_NON_RECURRING", "5734", 2500, 120000, "Legal"),
    "GUSTO": ("SOFTWARE_NON_RECURRING", "5734", 4900, 200000, "People"),
    "NOTION LABS": ("SOFTWARE_NON_RECURRING", "5734", 1000, 80000, "*"),
}
VENDORS = ["Larchmont Legal LLP", "Brightline Recruiting", "Summit Facilities Co", "Clearwater Accounting Group",
           "Northstar Design Partners", "Keystone Insurance Brokers", "Pioneer Hardware Supply", "Atlas Cloud Hosting",
           "Beacon Marketing Agency", "Cobalt Security Consulting", "Evergreen Janitorial", "Riverbend Catering"]
GL = {"SOFTWARE_NON_RECURRING": "6410 Software & Subscriptions", "ADVERTISING_AND_MARKETING": "6110 Advertising",
      "AIRFARE": "6520 Travel - Airfare", "LODGING": "6530 Travel - Lodging", "TAXI_AND_RIDESHARE": "6540 Travel - Ground",
      "CAR_RENTAL": "6540 Travel - Ground", "RESTAURANTS": "6550 Meals & Entertainment",
      "OFFICE_SUPPLIES": "6610 Office Supplies", "ELECTRONICS": "1510 Computer Equipment", "SHIPPING": "6620 Postage & Shipping",
      "FACILITIES_EXPENSES": "6710 Rent & Facilities", "UTILITIES": "6720 Utilities", "TELEPHONY": "6730 Telephone & Internet",
      "EVENT_EXPENSES": "6120 Events & Conferences", "EDUCATION": "6810 Training & Education",
      "LEGAL_SERVICES": "6910 Legal Fees", "OTHER": "6990 Other Expenses"}
MEMOS = {"RESTAURANTS": ["Team lunch", "Client dinner", "Working lunch during offsite", "Candidate lunch"],
         "AIRFARE": ["Flight to customer onsite", "Conference travel", "Board meeting travel"],
         "LODGING": ["Hotel for customer visit", "Conference hotel", "Offsite lodging"],
         "SOFTWARE_NON_RECURRING": ["Monthly subscription", "Annual plan renewal", "Additional seats"],
         "ADVERTISING_AND_MARKETING": ["Q campaign spend", "Product launch ads", "Retargeting campaign"]}


def _id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:24]}"


def _money(cents, cur="USD"):
    return {"amount": int(cents), "currency": cur}


def _ts(d, rnd):
    return datetime(d.year, d.month, d.day, rnd.randint(7, 21), rnd.randint(0, 59), rnd.randint(0, 59),
                    tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _company(i):
    rnd = random.Random(1000 + i)
    a, b = NAME_A[i % len(NAME_A)], NAME_B[(i * 7 + i // len(NAME_A)) % len(NAME_B)]
    name = f"{a} {b}"
    if i >= len(NAME_A) * 4:
        name += f" {['Group', 'Co', 'Partners', 'Holdings', 'Collective'][i % 5]}"
    return rnd, name, INDUSTRY[b]


def build_company(i, specs):
    """One fictional company's Brex data: returns {relative file: bytes} plus receipt PDFs."""
    rnd, name, industry = _company(i)
    domain = safe(name.lower().replace(" ", ""), 40) + ".example"
    size = rnd.choice([15, 25, 40, 60, 90, 140, 220, 350])
    months = rnd.randint(9, 30)
    end = date(2026, 9, 30)
    start = date(end.year - (months // 12), ((end.month - months % 12 - 1) % 12) + 1, 1)
    hq = rnd.choice(CITIES)
    locs = [hq] + rnd.sample([c for c in CITIES if c != hq], rnd.randint(0, 3 if size > 60 else 1))
    locations = [{"id": _id("loc"), "name": f"{c[0]} office", "description": "Headquarters" if k == 0 else "Office",
                  "address": {"line1": f"{rnd.randint(10, 999)} {rnd.choice(STREETS)}", "line2": f"Floor {rnd.randint(2, 30)}",
                              "city": c[0], "state": c[1], "country": "US", "postal_code": c[2]}, "timezone": c[3]}
                 for k, c in enumerate(locs)]
    depts = [{"id": _id("dept"), "name": d, "description": f"{d} department"} for d in DEPTS
             if size > 40 or d in ("Engineering", "Sales", "Marketing", "Finance", "Operations", "Executive")]
    dept_by = {d["name"]: d for d in depts}
    users = []
    used = set()
    for k in range(size):
        while True:
            fn, ln = rnd.choice(FIRST), rnd.choice(LAST)
            if (fn, ln) not in used:
                used.add((fn, ln))
                break
        dname = "Executive" if k < 3 else rnd.choices(
            [d["name"] for d in depts], [5 if d["name"] in ("Engineering", "Sales") else 2 for d in depts])[0]
        users.append({"id": _id("cuuser"), "first_name": fn, "last_name": ln,
                      "email": f"{fn.lower()}.{ln.lower()}@{domain}",
                      "status": rnd.choices(["ACTIVE", "INVITED", "DISABLED"], [92, 3, 5])[0],
                      "manager_id": None, "department_id": dept_by[dname]["id"],
                      "location_id": rnd.choice(locations)["id"], "metadata": {}, "_dept": dname})
    for u in users[3:]:
        same = [m for m in users[:max(4, size // 6)] if m["_dept"] == u["_dept"] and m is not u]
        u["manager_id"] = (same[0] if same else users[0])["id"]
    cards = []
    for u in users:
        if u["status"] == "INVITED":
            continue
        cards.append({"id": _id("cucard"), "owner": {"type": "USER", "user_id": u["id"]},
                      "status": "ACTIVE" if u["status"] == "ACTIVE" else "TERMINATED",
                      "last_four": f"{rnd.randint(0, 9999):04d}", "card_name": f"{u['first_name']} {u['last_name']}",
                      "card_type": "PHYSICAL", "limit_type": "USER",
                      "spend_controls": None, "expiration_date": {"month": rnd.randint(1, 12), "year": 2029},
                      "has_been_transferred": False, "metadata": {}, "created_at": _ts(start, rnd), "_user": u})
        if u["_dept"] in ("Engineering", "Marketing", "IT") and rnd.random() < 0.3:
            m = rnd.choice([k for k, v in MERCHANTS.items() if v[4] == u["_dept"]] or list(MERCHANTS))
            cards.append({"id": _id("cucard"), "owner": {"type": "USER", "user_id": u["id"]}, "status": "ACTIVE",
                          "last_four": f"{rnd.randint(0, 9999):04d}", "card_name": f"{m.title()} vendor card",
                          "card_type": "VIRTUAL", "limit_type": "CARD",
                          "spend_controls": {"spend_limit": _money(rnd.choice([50000, 200000, 1000000])),
                                             "spend_duration": "MONTHLY", "lock_after_date": None},
                          "expiration_date": {"month": rnd.randint(1, 12), "year": 2028}, "has_been_transferred": False,
                          "metadata": {}, "created_at": _ts(start, rnd), "_user": u, "_merchant": m})
    budgets, limits = [], []
    for d in depts:
        bid = _id("budget")
        amt = rnd.choice([500000, 1500000, 3000000, 8000000]) * (size // 15 + 1)
        budgets.append({"budget_id": bid, "account_id": _id("cuacc"), "creator_user_id": users[0]["id"],
                        "name": f"{d['name']} {end.year}", "description": f"Annual {d['name'].lower()} budget",
                        "parent_budget_id": None, "owner_user_ids": [users[0]["id"]], "member_user_ids":
                        [u["id"] for u in users if u["department_id"] == d["id"]][:50], "period_type": "YEARLY",
                        "start_date": f"{end.year}-01-01", "end_date": f"{end.year}-12-31", "limit": _money(amt),
                        "budget_status": "APPROVED", "limit_type": "HARD" if d["name"] == "Marketing" else "SOFT",
                        "spend_type": "NON_BUDGET_PROVISIONED_CARDS_ALLOWED", "limit_visibility": "SHARED",
                        "budget_type": "BUDGET"})
        for kind, per, lim in (("Travel", "PER_MONTH", 300000), ("Meals", "PER_MONTH", 60000),
                               ("Software", "PER_MONTH", 200000)):
            limits.append({"id": _id("sl"), "account_id": budgets[-1]["account_id"], "name": f"{d['name']} {kind}",
                           "description": f"{kind} spend for {d['name']}", "parent_budget_id": bid,
                           "status": "ACTIVE", "period_recurrence_type": per, "start_date": f"{end.year}-01-01",
                           "end_date": None, "authorization_settings": {"base_limit": _money(lim * (1 + size // 50)),
                                                                        "authorization_type": "SOFT"},
                           "expense_visibility": "SHARED", "spend_type": "BUDGET_PROVISIONED_CARDS_ONLY",
                           "department_id": d["id"],
                           "owner_user_ids": [users[0]["id"]], "member_user_ids": budgets[-1]["member_user_ids"]})
    budget_of = {b["name"].split(" ")[0]: b["budget_id"] for b in budgets}
    statuses = _enum(specs, "expenses", "ExpenseStatus")
    tx, expenses, trips, bookings = [], [], [], []
    day = start
    merchants = list(MERCHANTS.items())
    active = [c for c in cards if c["status"] == "ACTIVE"]
    while day <= end:
        for c in active:
            u = c["_user"]
            if c["card_type"] == "VIRTUAL":
                if day.day != 3:
                    continue
                pick = [(c["_merchant"], MERCHANTS[c["_merchant"]])]
            else:
                rate = 0.12 if u["_dept"] in ("Sales", "Executive") else 0.05
                if rnd.random() > rate or day.weekday() >= 5 and rnd.random() > 0.2:
                    continue
                pick = [rnd.choice([m for m in merchants if m[1][4] in ("*", u["_dept"])])]
            for desc, (cat, mcc, lo, hi, _) in pick:
                cents = int(rnd.lognormvariate(0, 0.6) * (lo + hi) / 6)
                cents = max(lo, min(hi, cents))
                tid, eid = _id("cutx"), _id("expense")
                posted = day + timedelta(days=rnd.randint(1, 3))
                refund = rnd.random() < 0.015
                tx.append({"id": tid, "card_id": c["id"], "description": desc, "amount": _money(-cents if refund else cents),
                           "initiated_at_date": day.isoformat(), "posted_at_date": posted.isoformat(),
                           "type": "REFUND" if refund else "PURCHASE",
                           "merchant": {"raw_descriptor": f"{desc} {rnd.randint(100000, 999999)}", "mcc": mcc,
                                        "country": "USA"}, "card_metadata": {}, "expense_id": eid})
                stt = "SETTLED" if posted < end - timedelta(days=30) else rnd.choice(["SUBMITTED", "APPROVED", "SETTLED"])
                if rnd.random() < 0.02:
                    stt = "OUT_OF_POLICY"
                expenses.append({
                    "id": eid, "memo": rnd.choice(MEMOS.get(cat, ["Business expense"])), "location_id": u["location_id"],
                    "department_id": u["department_id"], "updated_at": _ts(posted, rnd), "category": cat,
                    "merchant_id": _id("merchant"), "merchant": {"raw_descriptor": desc, "mcc": mcc, "country": "USA"},
                    "receipts": [], "budget_id": budget_of.get(u["_dept"]), "expense_type": "CARD",
                    "original_amount": _money(cents), "billing_amount": _money(cents), "budget_amount": _money(cents),
                    "purchased_amount": _money(cents), "usd_equivalent_amount": _money(cents),
                    "purchased_at": _ts(day, rnd), "status": stt if stt in statuses else "APPROVED",
                    "payment_status": "CLEARED" if not refund else "REFUNDED", "user_id": u["id"],
                    "card_transaction_reference_id": tid, "submitted_at": _ts(posted, rnd),
                    "approved_at": _ts(posted + timedelta(days=1), rnd) if stt in ("APPROVED", "SETTLED") else None,
                    "_gl": GL.get(cat, GL["OTHER"]), "_user": f"{u['first_name']} {u['last_name']}", "_dept": u["_dept"]})
                if cat == "AIRFARE" and rnd.random() < 0.6:
                    trip = {"id": _id("trip"), "created_at": _ts(day, rnd), "updated_at": _ts(posted, rnd),
                            "name": f"{rnd.choice(locs)[0]} trip", "booker_user_id": u["id"], "status": "COMPLETED",
                            "traveler": {"user_id": u["id"]}, "starts_at": _ts(day + timedelta(days=7), rnd),
                            "ends_at": _ts(day + timedelta(days=9), rnd), "trip_reference": f"TR{rnd.randint(10**6, 10**7)}"}
                    trips.append(trip)
                    for btype in ("FLIGHT", "HOTEL"):
                        bookings.append({"id": _id("booking"), "created_at": trip["created_at"], "trip_id": trip["id"],
                                         "type": btype, "status": "COMPLETED", "source": "BREX_TRAVEL",
                                         "booking_reference": f"{rnd.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{rnd.randint(10000, 99999)}",
                                         "trip_reference": trip["trip_reference"]})
        day += timedelta(days=1)
    # reimbursements and bill payments to vendors
    vendors = [{"id": _id("vendor"), "company_name": v, "email": f"billing@{safe(v.lower().replace(' ', ''), 30)}.example",
                "phone": f"+1-555-{rnd.randint(100, 999)}-{rnd.randint(1000, 9999)}", "payment_accounts": []}
               for v in rnd.sample(VENDORS, rnd.randint(4, len(VENDORS)))]
    transfers = []
    m = date(start.year, start.month, 1)
    while m <= end:
        for v in vendors:
            if rnd.random() < 0.5:
                cents = rnd.randint(80000, 2500000)
                pdate = m + timedelta(days=rnd.randint(5, 25))
                transfers.append({"id": _id("transfer"), "counterparty": {"type": "VENDOR", "payment_instrument_id": v["id"]},
                                  "description": f"Invoice {rnd.randint(1000, 9999)}", "payment_type": rnd.choice(["ACH", "DOMESTIC_WIRE", "CHEQUE"]),
                                  "amount": _money(cents), "process_date": pdate.isoformat(), "status": "PROCESSED",
                                  "creator_user_id": users[rnd.randint(0, min(5, size - 1))]["id"],
                                  "created_at": _ts(pdate - timedelta(days=2), rnd), "display_name": v["company_name"],
                                  "external_memo": "Thank you"})
        m = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
    for _ in range(size // 3 * max(1, months // 6)):
        u = rnd.choice(users)
        d = start + timedelta(days=rnd.randint(0, max(0, (end - start).days)))
        cents = rnd.randint(1500, 45000)
        expenses.append({"id": _id("expense"), "memo": rnd.choice(["Mileage to client site", "Home office supplies",
                                                                   "Parking", "Internet stipend", "Team snacks"]),
                         "location_id": u["location_id"], "department_id": u["department_id"],
                         "updated_at": _ts(d, rnd), "category": rnd.choice(["VEHICLE_EXPENSES", "OFFICE_SUPPLIES", "TELEPHONY", "RESTAURANTS"]),
                         "receipts": [], "budget_id": budget_of.get(u["_dept"]), "expense_type": "REIMBURSEMENT",
                         "original_amount": _money(cents), "billing_amount": _money(cents), "purchased_amount": _money(cents),
                         "purchased_at": _ts(d, rnd), "status": "SETTLED", "payment_status": "CLEARED", "user_id": u["id"],
                         "_gl": "6990 Other Expenses", "_user": f"{u['first_name']} {u['last_name']}", "_dept": u["_dept"]})
    # monthly card statements and cash account activity (card balance collected from the cash account)
    statements, cash = [], []
    bal = 0
    m = date(start.year, start.month, 1)
    cash_bal = rnd.randint(20, 400) * 100_000_00
    while m <= end:
        nxt = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
        spend = sum(t["amount"]["amount"] for t in tx if m <= date.fromisoformat(t["posted_at_date"]) < nxt)
        statements.append({"id": _id("statement"), "start_balance": _money(bal), "end_balance": _money(bal + spend),
                           "period": {"start_date": m.isoformat(), "end_date": (nxt - timedelta(days=1)).isoformat()}})
        cash.append({"id": _id("cashtx"), "description": "Card balance collection", "amount": _money(-(bal + spend)),
                     "initiated_at_date": nxt.isoformat(), "posted_at_date": nxt.isoformat(),
                     "type": "CARD_COLLECTION", "transfer_id": None})
        cash.append({"id": _id("cashtx"), "description": "Interest", "amount": _money(int(cash_bal * 0.04 / 12)),
                     "initiated_at_date": nxt.isoformat(), "posted_at_date": nxt.isoformat(), "type": "INTEREST",
                     "transfer_id": None})
        for t in transfers:
            if m <= date.fromisoformat(t["process_date"]) < nxt:
                cash.append({"id": _id("cashtx"), "description": t["display_name"], "amount": _money(-t["amount"]["amount"]),
                             "initiated_at_date": t["process_date"], "posted_at_date": t["process_date"],
                             "type": "PAYMENT", "transfer_id": t["id"]})
        bal = 0
        m = nxt
    company = {"id": _id("cuacc"), "legal_name": f"{name}, Inc.", "industry": industry, "employees": size,
               "website": f"https://www.{domain}", "mailing_address": locations[0]["address"],
               "account_type": "BREX_CLASSIC", "data_from": start.isoformat(), "data_to": end.isoformat()}
    return name, company, locations, depts, users, cards, budgets, limits, tx, expenses, statements, cash, vendors, \
        transfers, trips, bookings


def _clean(rows):
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]


def _receipt_pdf(company, e, user):
    from reportlab.lib.pagesizes import A6
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A6)
    w, h = A6
    m = e["merchant"]["raw_descriptor"].title()
    amt = e["purchased_amount"]["amount"] / 100
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(w / 2, h - 40, m)
    c.setFont("Helvetica", 8)
    c.drawCentredString(w / 2, h - 54, f"Receipt  #{e['id'][-8:].upper()}")
    c.drawString(20, h - 80, f"Date: {e['purchased_at'][:10]}  {e['purchased_at'][11:16]}")
    c.drawString(20, h - 92, f"Customer: {user}  ({company})")
    y = h - 118
    sub = round(amt / 1.0825, 2)
    for label, val in (("Items", sub), ("Sales tax", round(amt - sub, 2))):
        c.drawString(20, y, label)
        c.drawRightString(w - 20, y, f"${val:,.2f}")
        y -= 12
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20, y - 6, "TOTAL")
    c.drawRightString(w - 20, y - 6, f"${amt:,.2f}")
    c.setFont("Helvetica", 7)
    c.drawString(20, y - 26, f"Card ending {random.Random(e['id']).randint(1000, 9999)}  -  APPROVED")
    c.showPage()
    c.save()
    return buf.getvalue()


def companies(sink, st):
    """150 fictional companies' Brex data, one folder each."""
    s = session()
    specs = {}
    for a in ("expenses", "team", "transactions"):
        r = get(s, f"{DEV}/_spec/openapi/{a}_api.yaml")
        specs[a] = yaml.safe_load(r.text) if r else None
    if not all(specs.values()):
        return 0
    n = 0
    i = st.get("brex_i", 0)
    while i < COMPANIES and not sink.full():
        (name, company, locations, depts, users, cards, budgets, limits, tx, expenses, statements, cash, vendors,
         transfers, trips, bookings) = build_company(i, specs)
        base = f"{BREX}/Company Datasets/{i + 1:03d} {name}"
        files = {"company.json": company, "locations.json": locations, "departments.json": depts,
                 "users.json": _clean(users), "cards.json": _clean(cards), "budgets.json": budgets,
                 "spend_limits.json": limits, "card_transactions.json": tx, "expenses.json": _clean(expenses),
                 "card_statements.json": statements, "cash_transactions.json": cash, "vendors.json": vendors,
                 "transfers.json": transfers, "trips.json": trips, "bookings.json": bookings}
        for fname, items in files.items():  # list endpoints return {"next_cursor", "items"}
            body = items if fname == "company.json" else {"next_cursor": None, "items": items}
            sink.write_text(f"{base}/API/{fname}", json.dumps(body, indent=1))
        user_name = {u["id"]: f"{u['first_name']} {u['last_name']}" for u in users}
        card_owner = {c["id"]: c["card_name"] for c in cards}
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["Transaction ID", "Initiated Date", "Posted Date", "Card", "Merchant", "MCC", "Type",
                    "Amount (USD)", "Expense ID"])
        for t in tx:
            w.writerow([t["id"], t["initiated_at_date"], t["posted_at_date"], card_owner.get(t["card_id"]),
                        t["description"], t["merchant"]["mcc"], t["type"], f"{t['amount']['amount'] / 100:.2f}",
                        t["expense_id"]])
        sink.write_text(f"{base}/Exports/card_transactions.csv", out.getvalue())
        wb = new_book()
        add_sheet(wb, "Expenses", ["Expense ID", "Date", "User", "Department", "Merchant", "Category", "GL Account",
                                   "Type", "Status", "Amount (USD)", "Memo"],
                  [[e["id"], e["purchased_at"][:10], e["_user"], e["_dept"],
                    (e.get("merchant") or {}).get("raw_descriptor", ""), e["category"], e["_gl"], e["expense_type"],
                    e["status"], e["purchased_amount"]["amount"] / 100, e["memo"]] for e in expenses],
                  {"User": 22, "Merchant": 22, "GL Account": 28, "Memo": 30})
        gl = {}
        for e in expenses:
            k = (e["purchased_at"][:7], e["_gl"])
            gl[k] = gl.get(k, 0) + e["purchased_amount"]["amount"] / 100
        add_sheet(wb, "GL Summary", ["Month", "GL Account", "Amount (USD)"],
                  [[k[0], k[1], round(v, 2)] for k, v in sorted(gl.items())], {"GL Account": 32})
        save_book(sink, f"{base}/Exports/expense_report.xlsx", wb)
        rnd = random.Random(i)
        carded = [e for e in expenses if e.get("merchant")]
        for e in rnd.sample(carded, min(25, len(carded))):
            sink.write_bytes(f"{base}/Receipts/{e['purchased_at'][:10]} {safe(e['merchant']['raw_descriptor'], 30)} "
                             f"{e['id'][-6:]}.pdf", _receipt_pdf(company["legal_name"], e, e["_user"]))
        i += 1
        st["brex_i"] = i
        n += 1
        del user_name
    return n


SOURCES = {"brex_reference": reference, "brex_companies": companies}
